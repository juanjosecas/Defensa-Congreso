import * as Phaser from "phaser";
import { GAME, Point, RectDef } from "../config/gameConfig";

export type Terrain = "street" | "plaza" | "building";
export type MovementMode = "attacker" | "foot" | "motorized";

function toRect(def: RectDef): Phaser.Geom.Rectangle {
  return new Phaser.Geom.Rectangle(def.x, def.y, def.width, def.height);
}

export class CongressMap {
  readonly plaza = toRect(GAME.map.plaza);
  readonly congress = toRect(GAME.map.congress);
  readonly streets = GAME.map.streets.map(toRect);
  readonly sectors = new Map(
    GAME.map.sectors.map((item) => [item.name, toRect(item.rect)] as const)
  );

  constructor(private readonly scene: Phaser.Scene) {}

  terrainAt(point: Point): Terrain {
    if (this.congress.contains(point.x, point.y)) return "building";
    if (this.plaza.contains(point.x, point.y)) return "plaza";
    if (this.streets.some((rect) => rect.contains(point.x, point.y))) return "street";
    return "building";
  }

  canEnter(point: Point, mode: MovementMode): boolean {
    const terrain = this.terrainAt(point);
    if (mode === "motorized") return terrain === "street";
    return terrain === "street" || terrain === "plaza";
  }

  clampMotion(oldPos: Phaser.Math.Vector2, newPos: Phaser.Math.Vector2, mode: MovementMode): Phaser.Math.Vector2 {
    if (this.canEnter(newPos, mode)) return newPos.clone();

    const xOnly = new Phaser.Math.Vector2(newPos.x, oldPos.y);
    if (this.canEnter(xOnly, mode)) return xOnly;

    const yOnly = new Phaser.Math.Vector2(oldPos.x, newPos.y);
    if (this.canEnter(yOnly, mode)) return yOnly;

    return oldPos.clone();
  }

  nearestValidPoint(point: Point, mode: MovementMode, searchRadius = 96, step = 12): Phaser.Math.Vector2 | null {
    const origin = new Phaser.Math.Vector2(point.x, point.y);
    if (this.canEnter(origin, mode)) return origin;

    for (let radius = step; radius <= searchRadius; radius += step) {
      const offsets = [
        [radius, 0], [-radius, 0], [0, radius], [0, -radius],
        [radius, radius], [radius, -radius], [-radius, radius], [-radius, -radius]
      ];

      for (const [dx, dy] of offsets) {
        const candidate = new Phaser.Math.Vector2(origin.x + dx, origin.y + dy);
        if (this.canEnter(candidate, mode)) return candidate;
      }
    }

    return null;
  }

  sectorForPoint(point: Point): string | null {
    for (const [name, rect] of this.sectors) {
      if (rect.contains(point.x, point.y)) return name;
    }
    return null;
  }

  draw(): void {
    this.scene.cameras.main.setBackgroundColor(GAME.map.background);

    for (const street of GAME.map.streets) {
      this.scene.add
        .rectangle(street.x, street.y, street.width, street.height, GAME.map.roadColor)
        .setOrigin(0);
    }

    this.scene.add
      .rectangle(GAME.map.plaza.x, GAME.map.plaza.y, GAME.map.plaza.width, GAME.map.plaza.height, GAME.map.parkColor)
      .setOrigin(0)
      .setStrokeStyle(2, 0x557d55);

    this.scene.add
      .rectangle(GAME.map.congress.x, GAME.map.congress.y, GAME.map.congress.width, GAME.map.congress.height, GAME.map.buildingColor)
      .setOrigin(0)
      .setStrokeStyle(3, 0x5f5041);

    this.scene.add.text(
      GAME.map.congress.x + GAME.map.congress.width / 2,
      GAME.map.congress.y + GAME.map.congress.height / 2,
      "CONGRESO",
      {
        fontFamily: "Arial",
        fontSize: "16px",
        color: "#3c3228"
      }
    ).setOrigin(0.5);

    for (const label of GAME.map.labels) {
      this.scene.add.text(label.x, label.y, label.text, {
        fontFamily: "Arial",
        fontSize: "11px",
        color: "#4b4b4b"
      });
    }

    for (const [name, rect] of this.sectors) {
      this.scene.add
        .rectangle(rect.x, rect.y, rect.width, rect.height)
        .setOrigin(0)
        .setStrokeStyle(1, 0x73695f, 0.7);

      this.scene.add.text(rect.x + 3, rect.y + 3, name, {
        fontFamily: "Arial",
        fontSize: "10px",
        color: "#5f5046"
      });
    }
  }
}
