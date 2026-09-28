# Defensa del Congreso

Prototipo en Pygame orientado a un simulador caotico de contencion alrededor de Plaza Congreso.

El objetivo no es ganar: el operativo termina cuando la presion sobre el Congreso llega al 100%. La puntuacion principal es el tiempo resistido.

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
- click izquierdo: seleccionar una unidad o desplegar sobre terreno libre
- click y arrastre: seleccion rectangular
- `Shift + click/drag`: agregar unidades a la seleccion
- click derecho: mover unidades seleccionadas
- `C`: iniciar formacion de cordon; luego marcar inicio y fin con dos clicks
- `H`: mantener posicion
- `[` / `]`: disminuir/aumentar velocidad de simulacion
- `Esc`: cancelar orden/seleccion
- `P`: pausa
- `R`: reiniciar

## Gameplay actual

- mapa esquematico basado en la red de calles alrededor de Plaza Congreso;
- edificios no transitables;
- peatones y manifestantes limitados a calle/plaza;
- motos e hidrantes limitados a calle;
- atacantes con estados de avance, espera/deambulacion y retroceso;
- hidrante con efecto de retraso y disuasion;
- infanteria y otras unidades de control pueden detener individuos;
- vallas con integridad: contienen hasta romperse;
- identificacion individual visible de atacantes y fuerzas;
- reservas limitadas;
- refuerzos programados durante la partida;
- multiples rutas de ingreso;
- oleadas indefinidas con escalamiento;
- eventos caoticos aleatorios;
- sectores defensivos con integridad independiente;
- presion acumulativa sobre el Congreso;
- estadisticas de detenidos, huidas, vallas rotas y brechas;
- tiempo de supervivencia como resultado principal.

Las estadisticas y reglas de balance se editan en `config/game.yaml`.
