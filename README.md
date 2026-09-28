# Defensa del Congreso

Prototipo en Pygame orientado a un simulador caotico de contencion alrededor de Plaza Congreso.

El objetivo ya no es "ganar": el operativo termina cuando la presion sobre el Congreso llega al 100%. La puntuacion principal es el tiempo resistido.

## Instalacion

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controles

- `1`: desplegar infanteria a pie
- `2`: desplegar infanteria con balas de goma
- `3`: desplegar camion hidrante
- `4`: desplegar policia motorizada
- `5`: desplegar infiltrado
- `6`: desplegar valla
- click izquierdo: seleccionar una unidad; sobre terreno libre, desplegar la unidad elegida
- Shift + click: seleccion multiple
- click derecho: mover unidades seleccionadas
- `H`: mantener posicion
- `P`: pausa
- `R`: reiniciar

## Cambios de arquitectura

- mapa esquematico basado en la red de calles alrededor de Plaza Congreso;
- multiples rutas de ingreso;
- reservas limitadas en lugar de dinero generado durante la partida;
- unidades de seguridad moviles;
- seleccion directa y orden de movimiento;
- oleadas indefinidas con escalamiento;
- eventos caoticos aleatorios;
- presion acumulativa sobre el Congreso;
- tiempo de supervivencia como resultado principal.

Las estadisticas siguen siendo parametros ficticios de gameplay y se editan en `config/game.yaml`.
