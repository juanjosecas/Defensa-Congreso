# Defensa del Congreso

Juego 2D de simulacion caotica y contencion, ejecutable directamente en navegador.

La implementacion principal usa **TypeScript + Phaser 4 + Vite**. El prototipo Python/Pygame se conserva temporalmente como referencia de la migracion, pero ya no es el runtime principal.

## Ejecutar localmente

Requiere Node.js 24 o compatible.

```bash
npm install
npm run dev
```

Vite muestra la URL local, normalmente:

```text
http://localhost:5173/Defensa-Congreso/
```

Build de produccion:

```bash
npm run build
```

El resultado queda en `dist/` y puede servirse como sitio estatico.

## Stack

- Phaser 4.2.1
- TypeScript
- Vite
- GitHub Actions
- GitHub Pages

## Gameplay migrado

La version web reutiliza la logica desarrollada en el prototipo Pygame:

- mapa esquematico de Plaza Congreso y calles cercanas;
- edificios no transitables;
- atacantes limitados a calle/plaza;
- motos e hidrantes limitados a calle;
- atacantes con estados `advance`, `loiter` y `retreat`;
- vallas con integridad y rotura;
- hidrante con retraso, empuje y disuasion;
- unidades de seguridad moviles;
- seleccion individual y rectangular;
- movimiento con boton derecho;
- formacion de cordon;
- reservas limitadas y refuerzos;
- oleadas progresivas;
- eventos aleatorios;
- sectores defensivos con integridad independiente;
- estadisticas de detenidos, huidas, vallas rotas y brechas;
- derrota inevitable por presion acumulativa;
- tiempo resistido como puntuacion principal.

## Controles

- `1`: infanteria
- `2`: infanteria con goma
- `3`: hidrante
- `4`: motorizada
- `5`: infiltrado
- `6`: valla
- click: seleccionar o desplegar
- click + arrastre: seleccion rectangular
- `Shift` + seleccion: agregar unidades
- boton derecho: mover seleccion
- `C`: formar cordon, luego marcar inicio y fin
- `H`: mantener posicion
- `[` / `]`: velocidad de simulacion
- `P`: pausa
- `Esc`: cancelar orden/seleccion
- `R`: reiniciar despues de la derrota

## Estructura web

```text
src/
├── config/
│   └── gameConfig.ts
├── entities/
│   ├── Attacker.ts
│   ├── Barrier.ts
│   └── SecurityUnit.ts
├── scenes/
│   └── GameScene.ts
├── systems/
│   └── EventSystem.ts
├── world/
│   └── CongressMap.ts
├── main.ts
└── style.css
```

## Deploy

El workflow `.github/workflows/pages.yml` compila `main` y publica `dist/` en GitHub Pages.

En GitHub debe configurarse:

`Settings -> Pages -> Build and deployment -> Source: GitHub Actions`

La URL esperada es:

```text
https://juanjosecas.github.io/Defensa-Congreso/
```

## Prototipo Python

Los archivos `main.py`, `game/`, `config/game.yaml` y `requirements.txt` pertenecen al prototipo original y se mantienen mientras se valida la equivalencia funcional de la version web.
