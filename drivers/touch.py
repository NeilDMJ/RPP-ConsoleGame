"""
Driver tactil XPT2046.
Convierte lecturas crudas del controlador en coordenadas de pantalla (0-239, 0-319).

Requiere calibracion: ejecutar calibrar() una vez y anotar los valores
MIN_X, MAX_X, MIN_Y, MAX_Y para tu modulo especifico.
"""
from machine import Pin, SPI
from utime import sleep_ms

# ── Calibracion (ajustar con calibrar()) ──────────────────────
# Valores tipicos — pueden variar entre modulos
_MIN_X = 200
_MAX_X = 3800
_MIN_Y = 300
_MAX_Y = 3700

_W = 240
_H = 320

# SPI separado para el touch (SPI1) segun la propuesta
_spi_touch = None
_cs_touch  = None


def init_touch():
    """Inicializa el bus SPI del controlador tactil."""
    global _spi_touch, _cs_touch
    _spi_touch = SPI(1, baudrate=1_000_000,
                     sck=Pin(10), mosi=Pin(11), miso=Pin(12))
    _cs_touch = Pin(13, Pin.OUT, value=1)


def _leer_raw(cmd):
    """Envia comando al XPT2046 y lee 2 bytes."""
    _cs_touch.value(0)
    _spi_touch.write(bytes([cmd]))
    data = _spi_touch.read(2)
    _cs_touch.value(1)
    return ((data[0] << 8) | data[1]) >> 3  # 12 bits utiles


def leer():
    """
    Devuelve (x, y) en coordenadas de pantalla, o None si no hay toque.
    x: 0 (izquierda) a 239 (derecha)
    y: 0 (arriba)    a 319 (abajo)
    """
    z1 = _leer_raw(0xB1)   # presion Z1
    z2 = _leer_raw(0xC1)   # presion Z2
    if z1 < 100 or z2 > 3900:
        return None         # sin toque o ruido

    rx = _leer_raw(0xD1)   # posicion X raw
    ry = _leer_raw(0x91)   # posicion Y raw

    # Mapear a coordenadas de pantalla
    x = int((_MAX_X - rx) * _W / (_MAX_X - _MIN_X))
    y = int((ry - _MIN_Y) * _H / (_MAX_Y - _MIN_Y))

    x = max(0, min(_W - 1, x))
    y = max(0, min(_H - 1, y))
    return x, y


def calibrar(display):
    """
    Rutina de calibracion interactiva.
    Muestra 4 puntos de calibracion y mide los valores raw.
    Imprime los valores a usar en _MIN_X, _MAX_X, _MIN_Y, _MAX_Y.
    """
    from drivers.display import BLANCO, NEGRO, ROJO
    puntos = [
        (20,  20,  "sup-izq"),
        (220, 20,  "sup-der"),
        (220, 300, "inf-der"),
        (20,  300, "inf-izq"),
    ]
    resultados = []
    display.clear()
    for px, py, nombre in puntos:
        display.fill_circle(px, py, 6, ROJO)
        display.draw_text8x8(60, 150, f"Toca: {nombre}", BLANCO)
        sleep_ms(300)
        # Esperar toque real
        while True:
            z1 = _leer_raw(0xB1)
            if z1 > 100:
                rx = _leer_raw(0xD1)
                ry = _leer_raw(0x91)
                resultados.append((px, py, rx, ry))
                sleep_ms(400)
                break
        display.fill_circle(px, py, 6, NEGRO)
    print("Resultados calibracion:")
    for r in resultados:
        print(f"  pantalla({r[0]},{r[1]}) -> raw({r[2]},{r[3]})")
