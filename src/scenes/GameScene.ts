import * as Phaser from "phaser";
import {
  AttackerKind,
  EventConfig,
  GAME,
  ReserveKind,
  SecurityKind
} from "../config/gameConfig";
import { Attacker } from "../entities/Attacker";
import { Barrier } from "../entities/Barrier";
import { SecurityUnit } from "../entities/SecurityUnit";
import { EventSystem } from "../systems/EventSystem";
import { CongressMap } from "../world/CongressMap";

export class GameScene extends Phaser.Scene {
  private world!: CongressMap;
  private eventSystem!: EventSystem;

  private attackers: Attacker[] = [];
  private securityUnits: SecurityUnit[] = [];
  private barriers: Barrier[] = [];

  private reserves: Record<ReserveKind, number> = {
    ...GAME.reserves
  };

  private placementMode: ReserveKind = "infanteria";
  private selectedUnits: SecurityUnit[] = [];

  private invasionPressure = 0;
  private survivalTime = 0;
  private preparationTime = GAME.game.preparationTime;
  private timeScale = 1;
  private gameOver = false;
  private paused = false;

  private waveIndex = 0;
  private waveQueue: AttackerKind[] = [];
  private waveRunning = false;
  private spawnTimer = 0;
  private nextWaveTimer = 0;

  private attackerUid = 0;
  private securityUid = 0;

  private selectionStart: Phaser.Math.Vector2 | null = null;
  private selectionRect: Phaser.GameObjects.Rectangle | null = null;

  private cordonMode = false;
  private cordonStart: Phaser.Math.Vector2 | null = null;
  private cordonPreview: Phaser.GameObjects.Line | null = null;

  private reinforcementIndex = 0;

  private sectorIntegrity = new Map<string, number>();
  private sectorTexts = new Map<string, Phaser.GameObjects.Text>();

  private eventMessage = "Prepare el operativo.";
  private eventMessageTimer = 4;

  private stats = {
    detained: 0,
    fled: 0,
    barriersBroken: 0,
    breaches: 0
  };

  private statusText!: Phaser.GameObjects.Text;
  private reservesText!: Phaser.GameObjects.Text;
  private modeText!: Phaser.GameObjects.Text;
  private eventText!: Phaser.GameObjects.Text;
  private statsText!: Phaser.GameObjects.Text;
  private helpText!: Phaser.GameObjects.Text;

  constructor() {
    super("GameScene");
  }

  create(): void {
    this.world = new CongressMap(this);
    this.world.draw();

    for (const name of this.world.sectors.keys()) {
      this.sectorIntegrity.set(name, 100);
    }

    this.eventSystem = new EventSystem(
      GAME.events,
      GAME.eventSystem.minDelay,
      GAME.eventSystem.maxDelay
    );

    this.createUi();
    this.bindInput();

    this.game.canvas.addEventListener("contextmenu", (event) => {
      event.preventDefault();
    });
  }

  update(_time: number, deltaMs: number): void {
    if (this.paused || this.gameOver) {
      this.refreshUi();
      return;
    }

    const dt = (deltaMs / 1000) * this.timeScale;

    this.survivalTime += dt;
    this.eventMessageTimer = Math.max(0, this.eventMessageTimer - dt);

    this.updateWave(dt);
    this.updateReinforcements();
    this.handleEvent(this.eventSystem.update(dt));

    for (const attacker of this.attackers) {
      const wasAlive = attacker.alive;

      attacker.update(
        dt,
        this.barriers,
        this.securityUnits,
        this.world
      );

      if (wasAlive && !attacker.alive) {
        if (attacker.detained) this.stats.detained += 1;
        if (attacker.fled) this.stats.fled += 1;
      }

      if (attacker.reachedGoal) {
        this.invasionPressure += attacker.breachPower;
        this.stats.breaches += 1;
        attacker.reachedGoal = false;
      }
    }

    for (const unit of this.securityUnits) {
      unit.update(dt, this.attackers, this.world);
    }

    const previousBarrierCount = this.barriers.length;

    this.attackers = this.attackers.filter(
      (attacker) => attacker.alive
    );

    this.barriers = this.barriers.filter(
      (barrier) => barrier.alive
    );

    this.stats.barriersBroken +=
      previousBarrierCount - this.barriers.length;

    this.updateSectorPressure(dt);

    if (this.invasionPressure >= 100) {
      this.invasionPressure = 100;
      this.gameOver = true;
      this.eventMessage = "El Congreso fue invadido.";
      this.eventMessageTimer = Number.POSITIVE_INFINITY;
    }

    this.refreshUi();
  }

  private bindInput(): void {
    this.input.on(
      "pointerdown",
      (pointer: Phaser.Input.Pointer) => {
        if (pointer.y <= 88) return;

        if (pointer.rightButtonDown()) {
          this.orderMove(pointer.x, pointer.y);
          return;
        }

        if (!pointer.leftButtonDown()) return;

        if (this.cordonMode) {
          this.handleCordonClick(pointer.x, pointer.y);
          return;
        }

        this.selectionStart = new Phaser.Math.Vector2(
          pointer.x,
          pointer.y
        );

        this.selectionRect = this.add
          .rectangle(
            pointer.x,
            pointer.y,
            1,
            1,
            0x5082dc,
            0.15
          )
          .setOrigin(0)
          .setStrokeStyle(1, 0x4678dc);
      }
    );

    this.input.on(
      "pointermove",
      (pointer: Phaser.Input.Pointer) => {
        if (
          this.cordonMode &&
          this.cordonStart &&
          this.cordonPreview
        ) {
          this.cordonPreview.setTo(
            this.cordonStart.x,
            this.cordonStart.y,
            pointer.x,
            pointer.y
          );
        }

        if (!pointer.isDown || !this.selectionStart || !this.selectionRect) {
          return;
        }

        const x = Math.min(this.selectionStart.x, pointer.x);
        const y = Math.min(this.selectionStart.y, pointer.y);
        const width = Math.abs(pointer.x - this.selectionStart.x);
        const height = Math.abs(pointer.y - this.selectionStart.y);

        this.selectionRect
          .setPosition(x, y)
          .setSize(width, height)
          .setDisplaySize(width, height);
      }
    );

    this.input.on(
      "pointerup",
      (pointer: Phaser.Input.Pointer) => {
        if (!this.selectionStart) return;

        const end = new Phaser.Math.Vector2(pointer.x, pointer.y);
        const distance = this.selectionStart.distance(end);
        const additive = pointer.event.shiftKey;

        this.selectionRect?.destroy();
        this.selectionRect = null;

        if (distance >= 8) {
          this.selectRectangle(
            this.selectionStart,
            end,
            additive
          );
        } else {
          const selected = this.selectAt(
            pointer.x,
            pointer.y,
            additive
          );

          if (!selected && !additive) {
            this.clearSelection();
            this.deploy(pointer.x, pointer.y);
          }
        }

        this.selectionStart = null;
      }
    );

    this.input.keyboard?.on(
      "keydown",
      (event: KeyboardEvent) => {
        const modes: Partial<Record<string, ReserveKind>> = {
          Digit1: "infanteria",
          Digit2: "goma",
          Digit3: "hidrante",
          Digit4: "motorizada",
          Digit5: "infiltrado",
          Digit6: "barrier"
        };

        const mode = modes[event.code];
        if (mode) {
          this.placementMode = mode;
          this.refreshUi();
          return;
        }

        if (event.code === "KeyC") {
          this.beginCordon();
        } else if (event.code === "KeyH") {
          this.selectedUnits.forEach((unit) => unit.hold());
        } else if (event.code === "BracketLeft") {
          this.timeScale = Math.max(0.5, this.timeScale / 2);
        } else if (event.code === "BracketRight") {
          this.timeScale = Math.min(4, this.timeScale * 2);
        } else if (event.code === "KeyP") {
          this.paused = !this.paused;
        } else if (event.code === "Escape") {
          this.cancelOrders();
        } else if (event.code === "KeyR" && this.gameOver) {
          this.scene.restart();
        }

        this.refreshUi();
      }
    );
  }

  private deploy(x: number, y: number): void {
    if (this.reserves[this.placementMode] <= 0) return;

    if (this.placementMode === "barrier") {
      const point = this.world.nearestValidPoint(
        { x, y },
        "attacker"
      );

      if (!point) return;

      this.barriers.push(
        new Barrier(this, point.x, point.y)
      );

      this.reserves.barrier -= 1;
      return;
    }

    const kind = this.placementMode as SecurityKind;
    const cfg = GAME.security[kind];

    const mode =
      cfg.movementTerrain === "street_only"
        ? "motorized"
        : "foot";

    const point = this.world.nearestValidPoint(
      { x, y },
      mode
    );

    if (!point) return;

    this.securityUid += 1;

    this.securityUnits.push(
      new SecurityUnit(
        this,
        point.x,
        point.y,
        kind,
        cfg,
        this.securityUid
      )
    );

    this.reserves[kind] -= 1;
  }

  private clearSelection(): void {
    for (const unit of this.selectedUnits) {
      unit.setSelected(false);
    }

    this.selectedUnits = [];
  }

  private selectAt(
    x: number,
    y: number,
    additive: boolean
  ): boolean {
    const candidates = this.securityUnits.filter(
      (unit) => unit.containsPoint(x, y)
    );

    if (!additive) this.clearSelection();
    if (candidates.length === 0) return false;

    const point = new Phaser.Math.Vector2(x, y);

    candidates.sort(
      (a, b) =>
        a.pos.distance(point) - b.pos.distance(point)
    );

    const unit = candidates[0];
    unit.setSelected(true);

    if (!this.selectedUnits.includes(unit)) {
      this.selectedUnits.push(unit);
    }

    return true;
  }

  private selectRectangle(
    start: Phaser.Math.Vector2,
    end: Phaser.Math.Vector2,
    additive: boolean
  ): void {
    if (!additive) this.clearSelection();

    const rect = new Phaser.Geom.Rectangle(
      Math.min(start.x, end.x),
      Math.min(start.y, end.y),
      Math.abs(end.x - start.x),
      Math.abs(end.y - start.y)
    );

    for (const unit of this.securityUnits) {
      if (rect.contains(unit.pos.x, unit.pos.y)) {
        unit.setSelected(true);

        if (!this.selectedUnits.includes(unit)) {
          this.selectedUnits.push(unit);
        }
      }
    }
  }

  private orderMove(x: number, y: number): void {
    if (this.selectedUnits.length === 0) return;

    const target = new Phaser.Math.Vector2(x, y);
    const spacing = 24;
    const n = this.selectedUnits.length;

    this.selectedUnits.forEach((unit, index) => {
      const desired = target
        .clone()
        .add(
          new Phaser.Math.Vector2(
            (index - (n - 1) / 2) * spacing,
            0
          )
        );

      const mode =
        unit.movementTerrain === "street_only"
          ? "motorized"
          : "foot";

      const valid = this.world.nearestValidPoint(
        desired,
        mode
      );

      if (valid) unit.moveTo(valid);
    });
  }

  private beginCordon(): void {
    if (this.selectedUnits.length === 0) return;

    this.cordonMode = true;
    this.cordonStart = null;
    this.eventMessage = "Cordon: marque inicio y fin.";
    this.eventMessageTimer = 3;
  }

  private handleCordonClick(x: number, y: number): void {
    const point = new Phaser.Math.Vector2(x, y);

    if (!this.cordonStart) {
      this.cordonStart = point;

      this.cordonPreview = this.add
        .line(0, 0, x, y, x, y, 0xffd246)
        .setOrigin(0, 0)
        .setLineWidth(2);

      return;
    }

    const start = this.cordonStart;
    const count = this.selectedUnits.length;

    const targets =
      count === 1
        ? [start]
        : this.selectedUnits.map((_, index) =>
            start.clone().lerp(
              point,
              index / (count - 1)
            )
          );

    this.selectedUnits.forEach((unit, index) => {
      const mode =
        unit.movementTerrain === "street_only"
          ? "motorized"
          : "foot";

      const valid = this.world.nearestValidPoint(
        targets[index],
        mode,
        72
      );

      if (valid) unit.moveTo(valid);
    });

    this.cordonPreview?.destroy();
    this.cordonPreview = null;
    this.cordonMode = false;
    this.cordonStart = null;

    this.eventMessage = "Cordon desplegado.";
    this.eventMessageTimer = 2;
  }

  private cancelOrders(): void {
    this.selectionRect?.destroy();
    this.selectionRect = null;
    this.selectionStart = null;

    this.cordonPreview?.destroy();
    this.cordonPreview = null;
    this.cordonMode = false;
    this.cordonStart = null;

    this.clearSelection();
  }

  private updateWave(dt: number): void {
    if (this.preparationTime > 0) {
      this.preparationTime -= dt;
      return;
    }

    if (!this.waveRunning) {
      this.nextWaveTimer -= dt;

      if (this.nextWaveTimer <= 0) {
        this.beginWave();
      }

      return;
    }

    const wave = GAME.waves[
      this.waveIndex % GAME.waves.length
    ];

    if (this.waveQueue.length > 0) {
      this.spawnTimer -= dt;

      if (this.spawnTimer <= 0) {
        const kind = this.waveQueue.pop();
        if (kind) this.spawnAttacker(kind);
        this.spawnTimer = wave.interval;
      }

      return;
    }

    if (this.attackers.length === 0) {
      this.waveRunning = false;
      this.waveIndex += 1;
      this.nextWaveTimer = Math.max(
        2,
        7 - this.waveIndex * 0.25
      );
    }
  }

  private beginWave(): void {
    const wave = GAME.waves[
      this.waveIndex % GAME.waves.length
    ];

    const escalation =
      1 + Math.floor(this.waveIndex / GAME.waves.length);

    const queue: AttackerKind[] = [];

    for (const [kind, count] of Object.entries(
      wave.composition
    )) {
      for (let i = 0; i < count * escalation; i += 1) {
        queue.push(kind as AttackerKind);
      }
    }

    Phaser.Utils.Array.Shuffle(queue);

    this.waveQueue = queue;
    this.spawnTimer = 0;
    this.waveRunning = true;
  }

  private spawnAttacker(kind: AttackerKind): void {
    const spawn =
      GAME.spawnPoints[
        Phaser.Math.Between(
          0,
          GAME.spawnPoints.length - 1
        )
      ];

    const route = GAME.routes[spawn.route];

    this.attackerUid += 1;

    this.attackers.push(
      new Attacker(
        this,
        spawn.pos.x,
        spawn.pos.y + Phaser.Math.Between(-16, 16),
        kind,
        GAME.attackers[kind],
        route,
        this.attackerUid
      )
    );
  }

  private handleEvent(
    event: EventConfig | null
  ): void {
    if (!event) return;

    this.eventMessage = event.message;
    this.eventMessageTimer = 5.5;

    if ("composition" in event && event.composition) {
      for (const [kind, count] of Object.entries(
        event.composition
      )) {
        for (let i = 0; i < count; i += 1) {
          this.waveQueue.push(kind as AttackerKind);
        }
      }

      Phaser.Utils.Array.Shuffle(this.waveQueue);
    }

    if ("pressure" in event && event.pressure) {
      this.invasionPressure += event.pressure;
    }
  }

  private updateReinforcements(): void {
    while (
      this.reinforcementIndex <
      GAME.reinforcements.length
    ) {
      const item =
        GAME.reinforcements[this.reinforcementIndex];

      if (this.survivalTime < item.time) return;

      for (const [kind, count] of Object.entries(
        item.add
      )) {
        const key = kind as ReserveKind;
        this.reserves[key] += count;
      }

      this.eventMessage = item.message;
      this.eventMessageTimer = 5;
      this.reinforcementIndex += 1;
    }
  }

  private updateSectorPressure(dt: number): void {
    for (const [name, rect] of this.world.sectors) {
      const localAttackers = this.attackers.filter(
        (attacker) =>
          attacker.alive &&
          rect.contains(attacker.pos.x, attacker.pos.y)
      );

      let integrity =
        this.sectorIntegrity.get(name) ?? 100;

      if (localAttackers.length > 0) {
        const localPressure = localAttackers.reduce(
          (sum, attacker) =>
            sum + Math.max(0.3, attacker.breachPower / 8),
          0
        );

        integrity -=
          localPressure *
          GAME.game.sectorDamageRate *
          dt;
      } else {
        integrity +=
          GAME.game.sectorRecoveryRate * dt;
      }

      integrity = Phaser.Math.Clamp(
        integrity,
        0,
        100
      );

      this.sectorIntegrity.set(name, integrity);

      if (integrity <= 0) {
        this.invasionPressure +=
          GAME.game.sectorBreachPressure * dt;
      }
    }
  }

  private createUi(): void {
    this.add
      .rectangle(
        0,
        0,
        GAME.screen.width,
        88,
        0x232830,
        0.97
      )
      .setOrigin(0)
      .setDepth(100);

    this.statusText = this.add.text(
      14,
      8,
      "",
      this.uiStyle(19, "#f0f0f0")
    ).setDepth(101);

    this.reservesText = this.add.text(
      14,
      35,
      "",
      this.uiStyle(11, "#d2d7dc")
    ).setDepth(101);

    this.helpText = this.add.text(
      14,
      54,
      "1-6 despliegue | drag seleccion | RMB mover | C cordon | H mantener | [ ] velocidad | P pausa",
      this.uiStyle(13, "#cdd2d7")
    ).setDepth(101);

    this.modeText = this.add.text(
      14,
      72,
      "",
      this.uiStyle(13, "#ffdc78")
    ).setDepth(101);

    this.eventText = this.add.text(
      GAME.screen.width / 2,
      105,
      "",
      this.uiStyle(17, "#7d2323")
    ).setOrigin(0.5).setDepth(101);

    this.statsText = this.add.text(
      14,
      96,
      "",
      this.uiStyle(11, "#464646")
    ).setDepth(50);

    let y = 96;

    for (const name of this.world.sectors.keys()) {
      const text = this.add.text(
        GAME.screen.width - 235,
        y,
        "",
        this.uiStyle(11, "#424242")
      ).setDepth(50);

      this.sectorTexts.set(name, text);
      y += 16;
    }

    this.refreshUi();
  }

  private refreshUi(): void {
    const minutes = Math.floor(
      this.survivalTime / 60
    );

    const seconds = Math.floor(
      this.survivalTime % 60
    );

    const time = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    this.statusText.setText(
      `Tiempo ${time}   Presion ${this.invasionPressure.toFixed(1)}%   Oleada ${this.waveIndex + 1}   x${this.timeScale}${this.paused ? " PAUSA" : ""}`
    );

    this.reservesText.setText(
      "Reservas  " +
      Object.entries(this.reserves)
        .map(([key, value]) => `${key}:${value}`)
        .join("  ")
    );

    const modeLabel =
      this.placementMode === "barrier"
        ? "Valla"
        : GAME.security[
            this.placementMode as SecurityKind
          ].label;

    this.modeText.setText(
      `Despliegue: ${modeLabel}   Seleccionadas: ${this.selectedUnits.length}`
    );

    this.eventText.setText(
      this.eventMessageTimer > 0 || this.gameOver
        ? this.eventMessage
        : this.preparationTime > 0
          ? `PREPARACION: ${Math.ceil(this.preparationTime)}s`
          : ""
    );

    this.statsText.setText(
      `Detenidos ${this.stats.detained}   Huyeron ${this.stats.fled}   Vallas rotas ${this.stats.barriersBroken}   Brechas ${this.stats.breaches}`
    );

    for (const [name, text] of this.sectorTexts) {
      const integrity =
        this.sectorIntegrity.get(name) ?? 100;

      text.setText(
        `${name}: ${integrity.toFixed(1)}%`
      );
    }

    if (this.gameOver) {
      this.helpText.setText(
        `OPERATIVO FINALIZADO - resistio ${time} - R para reiniciar`
      );
    }
  }

  private uiStyle(
    fontSize: number,
    color: string
  ): Phaser.Types.GameObjects.Text.TextStyle {
    return {
      fontFamily: "Arial",
      fontSize: `${fontSize}px`,
      color
    };
  }
}
