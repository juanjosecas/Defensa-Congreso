import { EventConfig } from "../config/gameConfig";

export class EventSystem {
  private timer: number;

  constructor(
    private readonly events: readonly EventConfig[],
    private readonly minDelay: number,
    private readonly maxDelay: number
  ) {
    this.timer = this.randomDelay();
  }

  update(dtSeconds: number): EventConfig | null {
    if (this.events.length === 0) return null;

    this.timer -= dtSeconds;
    if (this.timer > 0) return null;

    this.timer = this.randomDelay();
    return this.events[Math.floor(Math.random() * this.events.length)] ?? null;
  }

  private randomDelay(): number {
    return this.minDelay + Math.random() * (this.maxDelay - this.minDelay);
  }
}
