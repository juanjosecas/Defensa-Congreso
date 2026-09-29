import * as Phaser from "phaser";
import {
  SecurityConfig,
  SecurityKind
} from "../config/gameConfig";
import type { Attacker } from "./Attacker";
import { CongressMap } from "../world/CongressMap";

export class SecurityUnit {
  readonly kind: SecurityKind;
  readonly pos: Phaser.Math.Vector2;
  readonly movementTerrain: "foot" | "street_only";
  readonly displayName: string;

  selected = false;

  private targetPos: Phaser.Math.Vector2;
  private cooldownTimer = 0;

  private readonly body: Phaser.GameObjects.Arc | Phaser.GameObjects.Rectangle;
  private readonly inner: Phaser.GameObjects.Arc | null;
  private readonly label: Phaser.GameObjects.Text;
  private readonly selectionRing: Phaser.GameObjects.Arc;
  private readonly rangeRing: Phaser.GameObjects.Arc;

  constructor(
    private readonly scene: Phaser.Scene,
    x: number,
    y: number,
    kind: SecurityKind,
    private readonly cfg: SecurityConfig,
    uid: number
  ) {
    this.kind = kind;
    this.pos = new Phaser.Math.Vector2(x, y);
    this.targetPos = this.pos.clone();
    this.movementTerrain = cfg.movementTerrain;
    this.displayName = `${cfg.shortLabel} ${String(uid).padStart(2, "0")}`;

    if (kind === "hidrante") {
      this.body = scene.add
        .rectangle(x, y, 36, 22, cfg.color)
        .setStrokeStyle(2, 0x26384a);
      this.inner = null;
    } else {
      this.body = scene.add
        .circle(x, y, cfg.radius, cfg.color)
        .setStrokeStyle(1, 0x26384a);

      this.inner = scene.add.circle(
        x,
        y,
        Math.max(3, cfg.radius / 3),
        0xe1ebff
      );
    }

    this.selectionRing = scene.add
      .circle(x, y, cfg.radius + 6, 0xffffff, 0)
      .setStrokeStyle(2, 0xffdc50)
      .setVisible(false);

    this.rangeRing = scene.add
      .circle(x, y, cfg.range, 0xffffff, 0)
      .setStrokeStyle(1, 0x555a69, 0.6)
      .setVisible(false);

    this.label = scene.add.text(x, y - 27, this.displayName, {
      fontFamily: "Arial",
      fontSize: "10px",
      color: "#142341",
      backgroundColor: "#edf2ffcc",
      padding: { x: 2, y: 1 }
    }).setOrigin(0.5);
  }

  setSelected(value: boolean): void {
    this.selected = value;
    this.selectionRing.setVisible(value);
    this.rangeRing.setVisible(value);
  }

  moveTo(point: Phaser.Math.Vector2): void {
    this.targetPos = point.clone();
  }

  hold(): void {
    this.targetPos = this.pos.clone();
  }

  containsPoint(x: number, y: number): boolean {
    return this.pos.distance(new Phaser.Math.Vector2(x, y)) <= this.cfg.radius + 8;
  }

  update(
    dt: number,
    attackers: readonly Attacker[],
    world: CongressMap
  ): Attacker[] {
    this.updateMovement(dt, world);
    this.cooldownTimer = Math.max(0, this.cooldownTimer - dt);

    const valid = attackers.filter(
      (attacker) =>
        attacker.alive &&
        this.pos.distance(attacker.pos) <= this.cfg.range
    );

    if (valid.length === 0) return [];

    if (this.cfg.effectType === "attract") {
      const affected: Attacker[] = [];
      const chance = (this.cfg.attractionChance ?? 0) * dt * 60;

      for (const attacker of valid) {
        if (Math.random() < chance) {
          attacker.attract(
            this.pos,
            this.cfg.attractionSeconds ?? 2.5
          );
          affected.push(attacker);
        }
      }

      return affected;
    }

    if (this.cooldownTimer > 0) return [];

    const target = valid.reduce((best, attacker) =>
      this.pos.distance(attacker.pos) < this.pos.distance(best.pos)
        ? attacker
        : best
    );

    if (this.cfg.effectType === "deterrent_area") {
      const areaRadius = this.cfg.areaRadius ?? 75;
      const affected = attackers.filter(
        (attacker) =>
          attacker.alive &&
          attacker.pos.distance(target.pos) <= areaRadius
      );

      for (const attacker of affected) {
        attacker.applyDeterrence(
          this.cfg.deterrence ?? 20,
          this.cfg.slow,
          1.4
        );

        attacker.pushAway(
          this.pos,
          this.cfg.push ?? 25,
          world
        );
      }

      this.cooldownTimer = this.cfg.cooldown;
      return affected;
    }

    target.applyControl(
      this.cfg.power,
      this.cfg.slow,
      0.9
    );

    this.cooldownTimer = this.cfg.cooldown;
    return [target];
  }

  private updateMovement(dt: number, world: CongressMap): void {
    const delta = this.targetPos.clone().subtract(this.pos);
    if (delta.lengthSq() < 4) return;

    const step = this.cfg.moveSpeed * dt;
    let proposed: Phaser.Math.Vector2;

    if (delta.length() <= step) {
      proposed = this.targetPos.clone();
    } else {
      proposed = this.pos
        .clone()
        .add(delta.normalize().scale(step));
    }

    const mode =
      this.movementTerrain === "street_only"
        ? "motorized"
        : "foot";

    this.pos.copy(
      world.clampMotion(
        this.pos,
        proposed,
        mode
      )
    );

    this.syncVisuals();
  }

  private syncVisuals(): void {
    this.body.setPosition(this.pos.x, this.pos.y);
    this.inner?.setPosition(this.pos.x, this.pos.y);
    this.selectionRing.setPosition(this.pos.x, this.pos.y);
    this.rangeRing.setPosition(this.pos.x, this.pos.y);
    this.label.setPosition(this.pos.x, this.pos.y - 27);
  }
}
