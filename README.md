# Congreso Defense

Prototipo modular en Pygame. Las estadísticas son parámetros ficticios de gameplay y se editan en `config/game.yaml`.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Controles

- `1`: infantería a pie
- `2`: infantería con balas de goma
- `3`: camión hidrante
- `4`: policía motorizada
- `5`: infiltrado
- `6`: barrera
- click izquierdo: colocar
- `SPACE`: iniciar oleada
- `P`: pausa
- `R`: reiniciar

## Atacantes

La configuración incluye: jubilado, maestro, militante de izquierda, militante PJ, manifestante violento, transeúnte y periodista.

Cada arquetipo tiene velocidad, resistencia, umbral de huida y avoidance. Los valores se eligieron únicamente para diferenciarlos como piezas de juego.

## Efectos especiales

- Infantería: control cercano + ralentización.
- Goma: control a distancia.
- Hidrante: efecto de área, empuje y ralentización.
- Motorizada: respuesta rápida con cooldown corto.
- Infiltrado: no aplica control; aleatoriamente atrae unidades cercanas durante unos segundos.
- Transeúnte: intenta apartarse de unidades de seguridad cercanas.
