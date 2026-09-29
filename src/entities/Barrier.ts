import * as Phaser from "phaser";
import { GAME } from "../config/gameConfig";

export class Barrier {
  readonly pos: Phaser.Math.Vector2;
  health = GAME.barrier.health;
  alive = true;

  private readonly body: Phaser.GameObjects.Rectangle;
  private readonly healthBg: Phaser.GameObjects.Rectangle;
  private readonly healthFg: Phaser.GameObjects.Rectangle;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    this.pos = new Phaser.Math.Vector2(x, y);

    this.body = scene.add
      .rectangle(x, y, GAME.barrier.width, GAME.barrier.height, 0xaa8c50)
      .setStrokeStyle(2, 0x5a4628);

    this.healthBg = scene.add.rectangle(
      x,
      y - GAME.barrier.height / 2 - 6,
      GAME.barrier.width,
      4,
      0x414141
    );

    this.healthFg = scene.add.rectangle(
      x - GAME.barrier.width / 2,
      y - GAME.barrier.height / 2 - 6,
      GAME.barrier.width,
      4,
      0x46aa50
    ).setOrigin(0, 0.5);
  }

  takeDamage(amount: number): void {
    if (!this.alive) return;

    this.health -= amount;
    const ratio = Phaser.Math.Clamp(this.health / GAME.barrier.health, 0, 1);
    this.healthFg.width = GAME.barrier.width * ratio;

    if (this.health <= 0) {
      this.alive = false;
      this.destroy();
    }
  }

  destroy(): void {
    this.body.destroy();
    this.healthBg.destroy();
    this.healthFg.destroy();
  }
}
