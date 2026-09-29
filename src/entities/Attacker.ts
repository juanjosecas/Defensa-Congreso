import * as Phaser from "phaser";
import {
  AttackerConfig,
  AttackerKind,
  Point
} from "../config/gameConfig";
import { Barrier } from "./Barrier";
import type { SecurityUnit } from "./SecurityUnit";
import { CongressMap } from "../world/CongressMap";

export type AttackerState = "advance" | "loiter" | "retreat";

export class Attacker {
  readonly kind: AttackerKind;
  readonly pos: Phaser.Math.Vector2;
  readonly spawn: Phaser.Math.Vector2;
  readonly displayName: string;
  readonly breachPower: number;

  alive = true;
  reachedGoal = false;
  fled = false;
  detained = false;

  private routeIndex = 0;
  private resistance: number;
  private readonly maxResistance: number;
  private slowFactor = 1;
  private slowTimer = 0;
  private deterrence = 0;
  private attractionTimer = 0;
  private attractedTo: Phaser.Math.Vector2 | null = null;

  state: AttackerState;
  private stateTimer: number;
  private loiterTarget: Phaser.Math.Vector2;

  private readonly body: Phaser.GameObjects.Arc;
  private readonly nameText: Phaser.GameObjects.Text;
  private readonly stateText: Phaser.GameObjects.Text;
  private readonly healthBg: Phaser.GameObjects.Rectangle;
  private readonly healthFg: Phaser.GameObjects.Rectangle;

  constructor(
    private readonly scene: Phaser.Scene,
    x: number,
    y: number,
    kind: AttackerKind,
    private readonly cfg: AttackerConfig,
    private readonly route: readonly Point[],
    uid: number
  ) {
    this.kind = kind;
    this.pos = new Phaser.Math.Vector2(x, y);
    this.spawn = this.pos.clone();
    this.displayName = `${cfg.shortLabel} ${String(uid).padStart(2, "0")}`;
    this.breachPower = cfg.breachPower;

    this.resistance = cfg.resistance;
    this.maxResistance = cfg.resistance;

    this.state = Math.random() < cfg.advanceWeight ? "advance" : "loiter";
    this.stateTimer = Phaser.Math.FloatBetween(2.5, 6.5);
    this.loiterTarget = this.pos.clone();

    this.body = scene.add
      .circle(x, y, cfg.radius, cfg.color)
      .setStrokeStyle(1, 0x2d2d2d);

    this.nameText = scene.add.text(x, y - 27, this.displayName, {
      fontFamily: "Arial",
      fontSize: "10px",
      color: "#222222",
      backgroundColor: "#f5f1e8cc",
      padding: { x: 2, y: 1 }
    }).setOrigin(0.5);

    this.stateText = scene.add.text(x, y - 40, "", {
      fontFamily: "Arial",
      fontSize: "9px",
      color: "#5c327a"
    }).setOrigin(0.5);

    this.healthBg = scene.add.rectangle(x, y - 16, 24, 4, 0x373737);
    this.healthFg = scene.add
      .rectangle(x - 12, y - 16, 24, 4, 0x50be5a)
      .setOrigin(0, 0.5);
  }

  applyControl(power: number, slow = 1, slowSeconds = 0.7): void {
    if (!this.alive) return;

    this.resistance -= power;

    if (slow < this.slowFactor) {
      this.slowFactor = slow;
      this.slowTimer = Math.max(this.slowTimer, slowSeconds);
    }

    const ratio = Math.max(0, this.resistance / this.maxResistance);

    if (this.cfg.fleeThreshold > 0 && ratio <= this.cfg.fleeThreshold) {
      this.fled = true;
      this.alive = false;
      this.destroy();
      return;
    }

    if (this.resistance <= 0) {
      this.detained = true;
      this.alive = false;
      this.destroy();
    }
  }

  applyDeterrence(amount: number, slow = 0.55, seconds = 1.3): void {
    if (!this.alive) return;

    this.deterrence = Math.min(100, this.deterrence + amount);

    if (slow < this.slowFactor) {
      this.slowFactor = slow;
      this.slowTimer = Math.max(this.slowTimer, seconds);
    }

    if (
      this.deterrence >= this.cfg.deterrenceThreshold ||
      Math.random() < amount / 300
    ) {
      this.state = "retreat";
      this.stateTimer = Phaser.Math.FloatBetween(2.5, 6);
      this.deterrence *= 0.55;
    }
  }

  attract(point: Phaser.Math.Vector2, seconds: number): void {
    this.attractedTo = point.clone();
    this.attractionTimer = Math.max(this.attractionTimer, seconds);
  }

  pushAway(source: Phaser.Math.Vector2, amount: number, world: CongressMap): void {
    const delta = this.pos.clone().subtract(source);
    if (delta.lengthSq() === 0) return;

    const proposed = this.pos.clone().add(delta.normalize().scale(amount));
    this.pos.copy(world.clampMotion(this.pos, proposed, "attacker"));
    this.syncVisuals();
  }

  update(
    dt: number,
    barriers: readonly Barrier[],
    securityUnits: readonly SecurityUnit[],
    world: CongressMap
  ): void {
    if (!this.alive) return;

    this.deterrence = Math.max(0, this.deterrence - 5 * dt);

    if (this.slowTimer > 0) {
      this.slowTimer -= dt;
    } else {
      this.slowFactor = 1;
    }

    let target: Phaser.Math.Vector2;
    const usingAttraction =
      this.attractionTimer > 0 && this.attractedTo !== null;

    if (usingAttraction && this.attractedTo) {
      this.attractionTimer -= dt;
      target = this.attractedTo;
    } else {
      this.attractedTo = null;
      target = this.behaviorTarget(dt, world);
    }

    let direction = target.clone().subtract(this.pos);

    if (
      this.state === "advance" &&
      !usingAttraction &&
      direction.lengthSq() < 18 * 18
    ) {
      this.routeIndex += 1;

      if (this.routeIndex >= this.route.length) {
        this.alive = false;
        this.reachedGoal = true;
        this.destroy();
        return;
      }

      target = this.routeTarget();
      direction = target.clone().subtract(this.pos);
    }

    if (direction.lengthSq() > 0) {
      direction.normalize();
    }

    if (this.cfg.policeAvoidance > 0) {
      const avoidance = new Phaser.Math.Vector2();

      for (const unit of securityUnits) {
        const delta = this.pos.clone().subtract(unit.pos);
        const dist = delta.length();

        if (dist > 0 && dist < 105) {
          avoidance.add(delta.normalize().scale((105 - dist) / 105));
        }
      }

      if (avoidance.lengthSq() > 0) {
        direction
          .add(avoidance.normalize().scale(this.cfg.policeAvoidance))
          .normalize();
      }
    }

    let barrierFactor = 1;

    for (const barrier of barriers) {
      if (!barrier.alive) continue;

      if (this.pos.distance(barrier.pos) < 42) {
        barrier.takeDamage(this.cfg.barrierDamage * dt);
        barrierFactor = 0;
      }
    }

    const proposed = this.pos.clone().add(
      direction.scale(
        this.cfg.speed * this.slowFactor * barrierFactor * dt
      )
    );

    this.pos.copy(world.clampMotion(this.pos, proposed, "attacker"));
    this.syncVisuals();
  }

  containsPoint(x: number, y: number): boolean {
    return this.pos.distance(new Phaser.Math.Vector2(x, y)) <= this.cfg.radius + 4;
  }

  private behaviorTarget(dt: number, world: CongressMap): Phaser.Math.Vector2 {
    if (this.state === "retreat") {
      this.stateTimer -= dt;

      if (this.stateTimer <= 0) {
        this.chooseBehavior();
      }

      return this.retreatTarget();
    }

    if (this.state === "loiter") {
      this.stateTimer -= dt;

      if (this.pos.distance(this.loiterTarget) < 14) {
        this.chooseLoiterTarget(world);
      }

      if (this.stateTimer <= 0) {
        this.chooseBehavior();
      }

      return this.loiterTarget;
    }

    this.stateTimer -= dt;

    if (this.stateTimer <= 0 && Math.random() < 0.3) {
      this.state = "loiter";
      this.stateTimer = Phaser.Math.FloatBetween(2, 5);
      this.chooseLoiterTarget(world);
      return this.loiterTarget;
    }

    return this.routeTarget();
  }

  private chooseBehavior(): void {
    this.state =
      Math.random() < this.cfg.advanceWeight ? "advance" : "loiter";
    this.stateTimer = Phaser.Math.FloatBetween(2.5, 7);
  }

  private chooseLoiterTarget(world: CongressMap): void {
    for (let i = 0; i < 18; i += 1) {
      const candidate = this.pos.clone().add(
        new Phaser.Math.Vector2(
          Phaser.Math.FloatBetween(-95, 95),
          Phaser.Math.FloatBetween(-95, 95)
        )
      );

      if (world.canEnter(candidate, "attacker")) {
        this.loiterTarget = candidate;
        return;
      }
    }

    this.loiterTarget = this.pos.clone();
  }

  private routeTarget(): Phaser.Math.Vector2 {
    const point = this.route[Math.min(this.routeIndex, this.route.length - 1)];
    return new Phaser.Math.Vector2(point.x, point.y);
  }

  private retreatTarget(): Phaser.Math.Vector2 {
    if (this.routeIndex > 1) {
      const point = this.route[this.routeIndex - 2];
      return new Phaser.Math.Vector2(point.x, point.y);
    }

    return this.spawn.clone();
  }

  private syncVisuals(): void {
    const ratio = Phaser.Math.Clamp(
      this.resistance / this.maxResistance,
      0,
      1
    );

    this.body.setPosition(this.pos.x, this.pos.y);
    this.nameText.setPosition(this.pos.x, this.pos.y - 27);
    this.stateText
      .setText(this.state === "retreat" ? "retrocede" : "")
      .setPosition(this.pos.x, this.pos.y - 40);

    this.healthBg.setPosition(this.pos.x, this.pos.y - 16);
    this.healthFg
      .setPosition(this.pos.x - 12, this.pos.y - 16)
      .setDisplaySize(24 * ratio, 4);
  }

  private destroy(): void {
    this.body.destroy();
    this.nameText.destroy();
    this.stateText.destroy();
    this.healthBg.destroy();
    this.healthFg.destroy();
  }
}
