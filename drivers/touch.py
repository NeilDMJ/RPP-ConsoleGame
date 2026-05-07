"""
Driver tactil XPT2046 — SPI0 (separado de la pantalla que usa SPI1).
SCK=GP18, MOSI=GP19, MISO=GP16, CS=GP13, IRQ=GP8
Orientacion landscape 320x240.
"""
from machine import Pin, SPI
from utime import sleep_ms

# ── Calibracion ───────────────────────────────────────────────
_MIN_X = 200
_MAX_X = 3800
_MIN_Y = 300
_MAX_Y = 3700

# Dimensiones landscape
_W = 320
_H = 240

_spi_touch = None
_cs_touch  = None
_irq       = None


def init_touch():
    global _spi_touch, _cs_touch, _irq
    # SPI0 — completamente separado del SPI1 de la pantalla
    _spi_touch = SPI(0, baudrate=1_000_000,
                     sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    _cs_touch  = Pin(13, Pin.OUT, value=1)
    _irq       = Pin(8,  Pin.IN,  Pin.PULL_UP)


def hay_toque():
    """Consulta rapida sin leer SPI. True si hay dedo en la pantalla."""
    return _irq is not None and _irq.value() == 0


def _leer_raw(cmd):
    _cs_touch.value(0)
    _spi_touch.write(bytes([cmd]))
    data = _spi_touch.read(2)
    _cs_touch.value(1)
    return ((data[0] << 8) | data[1]) >> 3


def leer():
    """
    Devuelve (x, y) en coordenadas landscape (0-319, 0-239), o None.
    Solo llama si hay_toque() es True para no desperdiciar ciclos.
    """
    if not hay_toque():
        return None

    z1 = _leer_raw(0xB1)
    z2 = _leer_raw(0xC1)
    if z1 < 100 or z2 > 3900:
        _leer_raw(0x90)
        return None

    # Promediar 3 lecturas para mayor precision (ADC encendido)
    rx = (_leer_raw(0xD1) + _leer_raw(0xD1) + _leer_raw(0xD1)) // 3
    ry = (_leer_raw(0x91) + _leer_raw(0x91) + _leer_raw(0x91)) // 3

    # Dummy read con power-down → rearma PENIRQ
    _leer_raw(0x90)

    # Mapear a landscape: X del touch -> X pantalla, Y touch -> Y pantalla
    x = int((_MAX_X - rx) * _W / (_MAX_X - _MIN_X))
    y = int((ry - _MIN_Y) * _H / (_MAX_Y - _MIN_Y))

    x = max(0, min(_W - 1, x))
    y = max(0, min(_H - 1, y))
    return x, y


def calibrar(display):
    """Calibracion interactiva. Ejecutar una vez y anotar los valores."""
    from drivers.display import BLANCO, NEGRO, ROJO
    puntos = [
        (20,  20,  "sup-izq"),
        (300, 20,  "sup-der"),
        (300, 220, "inf-der"),
        (20,  220, "inf-izq"),
    ]
    resultados = []
    display.clear()
    for px, py, nombre in puntos:
        display.fill_circle(px, py, 6, ROJO)
        display.draw_text8x8(80, 110, f"Toca: {nombre}", BLANCO)
        sleep_ms(300)
        while not hay_toque():
            sleep_ms(20)
        sleep_ms(50)
        rx = _leer_raw(0xD1)
        ry = _leer_raw(0x91)
        resultados.append((px, py, rx, ry))
        sleep_ms(400)
        display.fill_circle(px, py, 6, NEGRO)

    print("Calibracion — pega estos valores en touch.py:")
    xs = [r[2] for r in resultados]
    ys = [r[3] for r in resultados]
    print(f"_MIN_X = {min(xs)}")
    print(f"_MAX_X = {max(xs)}")
    print(f"_MIN_Y = {min(ys)}")
    print(f"_MAX_Y = {max(ys)}")