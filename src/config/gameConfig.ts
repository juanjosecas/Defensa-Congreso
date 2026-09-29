export type AttackerKind =
  | "jubilado"
  | "maestro"
  | "izquierda"
  | "pj"
  | "violento"
  | "transeunte"
  | "periodista";

export type SecurityKind =
  | "infanteria"
  | "goma"
  | "hidrante"
  | "motorizada"
  | "infiltrado";

export type ReserveKind = SecurityKind | "barrier";

export interface Point {
  x: number;
  y: number;
}

export interface RectDef {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AttackerConfig {
  label: string;
  shortLabel: string;
  speed: number;
  advanceWeight: number;
  loiterWeight: number;
  deterrenceThreshold: number;
  barrierDamage: number;
  resistance: number;
  fleeThreshold: number;
  policeAvoidance: number;
  breachPower: number;
  radius: number;
  color: number;
}

export interface SecurityConfig {
  label: string;
  shortLabel: string;
  moveSpeed: number;
  movementTerrain: "foot" | "street_only";
  range: number;
  power: number;
  cooldown: number;
  radius: number;
  effectType: "single" | "deterrent_area" | "attract";
  slow: number;
  color: number;
  areaRadius?: number;
  push?: number;
  deterrence?: number;
  attractionChance?: number;
  attractionSeconds?: number;
}

export interface EventConfig {
  message: string;
  composition?: Partial<Record<AttackerKind, number>>;
  pressure?: number;
}

export const GAME = {
  screen: {
    width: 1280,
    height: 720
  },

  game: {
    preparationTime: 14,
    sectorDamageRate: 2.8,
    sectorRecoveryRate: 0.55,
    sectorBreachPressure: 0.9
  },

  reserves: {
    infanteria: 18,
    goma: 6,
    hidrante: 2,
    motorizada: 5,
    infiltrado: 3,
    barrier: 24
  } satisfies Record<ReserveKind, number>,

  map: {
    background: 0xe1dccd,
    roadColor: 0xbcbec2,
    roadLine: 0xebebe6,
    parkColor: 0x9abe96,
    buildingColor: 0xbcaa8c,

    plaza: { x: 270, y: 285, width: 330, height: 190 } satisfies RectDef,
    congress: { x: 135, y: 300, width: 125, height: 175 } satisfies RectDef,

    streets: [
      { x: 0, y: 250, width: 1280, height: 72 },
      { x: 0, y: 400, width: 1280, height: 62 },
      { x: 0, y: 565, width: 1280, height: 58 },
      { x: 225, y: 88, width: 66, height: 632 },
      { x: 500, y: 88, width: 58, height: 632 },
      { x: 760, y: 88, width: 58, height: 632 },
      { x: 1010, y: 88, width: 70, height: 632 }
    ] satisfies RectDef[],

    sectors: [
      { name: "Norte", rect: { x: 250, y: 250, width: 210, height: 75 } },
      { name: "Plaza", rect: { x: 270, y: 325, width: 250, height: 150 } },
      { name: "Sur", rect: { x: 250, y: 400, width: 210, height: 70 } },
      { name: "Este", rect: { x: 460, y: 300, width: 170, height: 150 } }
    ],

    labels: [
      { text: "Av. Rivadavia", x: 610, y: 257 },
      { text: "Hipolito Yrigoyen", x: 610, y: 407 },
      { text: "Av. Belgrano", x: 610, y: 572 },
      { text: "Entre Rios / Callao", x: 228, y: 96 },
      { text: "Montevideo", x: 505, y: 96 },
      { text: "Uruguay", x: 765, y: 96 },
      { text: "San Jose", x: 1015, y: 96 }
    ]
  },

  spawnPoints: [
    { pos: { x: 1260, y: 285 }, route: "rivadaviaEste" },
    { pos: { x: 1260, y: 430 }, route: "yrigoyenEste" },
    { pos: { x: 1045, y: 700 }, route: "sanJoseSur" },
    { pos: { x: 785, y: 700 }, route: "uruguaySur" },
    { pos: { x: 530, y: 95 }, route: "montevideoNorte" },
    { pos: { x: 255, y: 95 }, route: "callaoNorte" }
  ],

  routes: {
    rivadaviaEste: [
      { x: 920, y: 286 },
      { x: 650, y: 286 },
      { x: 530, y: 330 },
      { x: 380, y: 360 },
      { x: 300, y: 380 },
      { x: 276, y: 385 }
    ],
    yrigoyenEste: [
      { x: 920, y: 430 },
      { x: 650, y: 430 },
      { x: 520, y: 430 },
      { x: 380, y: 410 },
      { x: 305, y: 400 },
      { x: 276, y: 385 }
    ],
    sanJoseSur: [
      { x: 1045, y: 580 },
      { x: 1045, y: 430 },
      { x: 820, y: 430 },
      { x: 590, y: 410 },
      { x: 380, y: 395 },
      { x: 276, y: 385 }
    ],
    uruguaySur: [
      { x: 785, y: 580 },
      { x: 785, y: 430 },
      { x: 600, y: 430 },
      { x: 430, y: 405 },
      { x: 320, y: 395 },
      { x: 276, y: 385 }
    ],
    montevideoNorte: [
      { x: 530, y: 210 },
      { x: 530, y: 300 },
      { x: 470, y: 335 },
      { x: 350, y: 365 },
      { x: 276, y: 385 }
    ],
    callaoNorte: [
      { x: 255, y: 210 },
      { x: 255, y: 300 },
      { x: 285, y: 345 },
      { x: 276, y: 385 }
    ]
  } satisfies Record<string, Point[]>,

  attackers: {
    jubilado: {
      label: "Jubilado",
      shortLabel: "Jub.",
      speed: 30,
      advanceWeight: 0.45,
      loiterWeight: 0.55,
      deterrenceThreshold: 38,
      barrierDamage: 2,
      resistance: 45,
      fleeThreshold: 0.7,
      policeAvoidance: 0.2,
      breachPower: 3,
      radius: 8,
      color: 0xb4a57d
    },
    maestro: {
      label: "Maestro",
      shortLabel: "Maestro",
      speed: 52,
      advanceWeight: 0.52,
      loiterWeight: 0.48,
      deterrenceThreshold: 45,
      barrierDamage: 3,
      resistance: 55,
      fleeThreshold: 0.65,
      policeAvoidance: 0.25,
      breachPower: 4,
      radius: 8,
      color: 0x509bcd
    },
    izquierda: {
      label: "Militante de izquierda",
      shortLabel: "Izq.",
      speed: 55,
      advanceWeight: 0.72,
      loiterWeight: 0.28,
      deterrenceThreshold: 72,
      barrierDamage: 7,
      resistance: 105,
      fleeThreshold: 0.22,
      policeAvoidance: 0.05,
      breachPower: 7,
      radius: 9,
      color: 0xcd4646
    },
    pj: {
      label: "Militante PJ",
      shortLabel: "PJ",
      speed: 53,
      advanceWeight: 0.7,
      loiterWeight: 0.3,
      deterrenceThreshold: 74,
      barrierDamage: 7,
      resistance: 110,
      fleeThreshold: 0.2,
      policeAvoidance: 0.05,
      breachPower: 7,
      radius: 9,
      color: 0x4b87d2
    },
    violento: {
      label: "Manifestante violento",
      shortLabel: "Violento",
      speed: 63,
      advanceWeight: 0.86,
      loiterWeight: 0.14,
      deterrenceThreshold: 88,
      barrierDamage: 15,
      resistance: 145,
      fleeThreshold: 0.08,
      policeAvoidance: 0,
      breachPower: 12,
      radius: 10,
      color: 0x642323
    },
    transeunte: {
      label: "Transeunte",
      shortLabel: "Transeunte",
      speed: 48,
      advanceWeight: 0.28,
      loiterWeight: 0.72,
      deterrenceThreshold: 28,
      barrierDamage: 1,
      resistance: 35,
      fleeThreshold: 0.85,
      policeAvoidance: 1,
      breachPower: 1,
      radius: 7,
      color: 0x919191
    },
    periodista: {
      label: "Periodista",
      shortLabel: "Prensa",
      speed: 50,
      advanceWeight: 0.42,
      loiterWeight: 0.58,
      deterrenceThreshold: 52,
      barrierDamage: 2,
      resistance: 70,
      fleeThreshold: 0.45,
      policeAvoidance: 0.35,
      breachPower: 5,
      radius: 8,
      color: 0xcdaf46
    }
  } satisfies Record<AttackerKind, AttackerConfig>,

  security: {
    infanteria: {
      label: "Infanteria a pie",
      shortLabel: "Inf.",
      moveSpeed: 78,
      movementTerrain: "foot",
      range: 72,
      power: 28,
      cooldown: 0.65,
      radius: 13,
      effectType: "single",
      slow: 0.65,
      color: 0x375fb9
    },
    goma: {
      label: "Infanteria con balas de goma",
      shortLabel: "Goma",
      moveSpeed: 72,
      movementTerrain: "foot",
      range: 210,
      power: 20,
      cooldown: 0.8,
      radius: 13,
      effectType: "single",
      slow: 0.9,
      color: 0x234691
    },
    hidrante: {
      label: "Camion hidrante",
      shortLabel: "Hidrante",
      moveSpeed: 42,
      movementTerrain: "street_only",
      range: 175,
      power: 0,
      deterrence: 26,
      cooldown: 1.25,
      radius: 18,
      effectType: "deterrent_area",
      areaRadius: 75,
      push: 34,
      slow: 0.42,
      color: 0x3791c3
    },
    motorizada: {
      label: "Policia motorizada",
      shortLabel: "Moto",
      moveSpeed: 150,
      movementTerrain: "street_only",
      range: 135,
      power: 18,
      cooldown: 0.38,
      radius: 14,
      effectType: "single",
      slow: 0.82,
      color: 0x2d4169
    },
    infiltrado: {
      label: "Infiltrado",
      shortLabel: "Infil.",
      moveSpeed: 62,
      movementTerrain: "foot",
      range: 165,
      power: 0,
      cooldown: 0.5,
      radius: 10,
      effectType: "attract",
      attractionChance: 0.01,
      attractionSeconds: 2.5,
      slow: 1,
      color: 0x785091
    }
  } satisfies Record<SecurityKind, SecurityConfig>,

  barrier: {
    width: 48,
    height: 20,
    radius: 42,
    blockFactor: 0,
    health: 190
  },

  reinforcements: [
    {
      time: 90,
      add: { infanteria: 4, barrier: 4 },
      message: "Llegaron cuatro infantes y un lote de vallas."
    },
    {
      time: 180,
      add: { goma: 2, motorizada: 2 },
      message: "Refuerzo tardio: goma y dos motos."
    },
    {
      time: 300,
      add: { hidrante: 1, infanteria: 4 },
      message: "Finalmente llego otro hidrante."
    }
  ],

  eventSystem: {
    minDelay: 16,
    maxDelay: 29
  },

  events: [
    {
      message: "Llegaron dos colectivos por Rivadavia.",
      composition: { pj: 5, transeunte: 2 }
    },
    {
      message: "Un grupo cambio de recorrido sin avisar.",
      composition: { izquierda: 4 }
    },
    {
      message: "Periodistas detectaron un incidente y se acercan.",
      composition: { periodista: 3 }
    },
    {
      message: "Jefatura pide reforzar el sector que acaba de quedar vacio.",
      composition: { violento: 2, pj: 2 }
    },
    {
      message: "El vallado no esta exactamente donde todos creian.",
      pressure: 2
    },
    {
      message: "El infiltrado asegura que tiene todo bajo control.",
      composition: { izquierda: 2, pj: 2 }
    },
    {
      message: "Aparecio una columna por una calle secundaria.",
      composition: { maestro: 1, izquierda: 3, transeunte: 2 }
    }
  ] satisfies EventConfig[],

  waves: [
    {
      interval: 0.78,
      composition: {
        jubilado: 2,
        maestro: 2,
        izquierda: 5,
        pj: 5,
        transeunte: 2
      }
    },
    {
      interval: 0.62,
      composition: {
        jubilado: 1,
        maestro: 2,
        izquierda: 8,
        pj: 8,
        periodista: 3,
        transeunte: 3
      }
    },
    {
      interval: 0.49,
      composition: {
        izquierda: 10,
        pj: 10,
        violento: 6,
        periodista: 4,
        transeunte: 4
      }
    },
    {
      interval: 0.39,
      composition: {
        jubilado: 1,
        maestro: 1,
        izquierda: 14,
        pj: 14,
        violento: 10,
        periodista: 6,
        transeunte: 5
      }
    }
  ]
} as const;
