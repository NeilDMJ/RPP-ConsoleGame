"""
Driver tactil XPT2046 (basado en rdagger/micropython-ili9341).
SPI0 separado del SPI1 de la pantalla.
SCK=GP18, MOSI=GP19, MISO=GP16, CS=GP13, IRQ=GP8

API publica (compatible con la version anterior):
  init_touch()  -> inicializa el hardware
  hay_toque()   -> bool, lectura rapida del PENIRQ
  leer()        -> (x, y) en landscape 320x240, o None
  calibrar(display) -> rutina interactiva de calibracion
"""
from machine import Pin, SPI
from utime import sleep_ms
from drivers.xpt2046 import Touch  # driver de rdagger

# ── Calibracion (los mismos valores que tenias) ───────────────
# OJO: en el driver de rdagger las "unidades raw" son 12-bit (0-4095),
# igual que en tu driver anterior, asi que los limites se conservan.
# Valores de tu calibracion real
_MIN_X = 0    # ny minimo (sup-izq)
_MAX_X = 150   # ny maximo (sup-der)
_MIN_Y = 6    # nx minimo (sup-izq)
_MAX_Y = 108    # nx maximo (inf-izq)

# Dimensiones LOGICAS (lo que ven tus juegos)
_W = 320
_H = 240

# El driver de rdagger trabaja en orientacion "nativa" del panel (240x320).
# Le pedimos que normalice a 240x320 y nosotros rotamos a landscape al final.
_NATIVE_W = 240
_NATIVE_H = 320

_touch = None
_irq   = None


def init_touch():
    global _touch, _irq

    spi = SPI(0, baudrate=1_000_000,
              sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    cs  = Pin(13, Pin.OUT, value=1)
    _irq = Pin(8, Pin.IN, Pin.PULL_UP)

    _touch = Touch(
        spi, cs,
        int_pin=None,          # no usamos el modo IRQ del driver; lo manejamos aparte
        int_handler=None,
        width=_NATIVE_W, height=_NATIVE_H,
        x_min=_MIN_X, x_max=_MAX_X,
        y_min=_MIN_Y, y_max=_MAX_Y,
    )


def hay_toque():
    """Consulta rapida del pin PENIRQ. True si hay dedo apoyado."""
    return _irq is not None and _irq.value() == 0


def leer():
    if _touch is None or not hay_toque():
        return None

    p = _touch.get_touch()
    if p is None:
        return None

    nx, ny = p

    # Mapeo correcto segun calibracion real:
    # ny varia con X de pantalla (izq->der):  22->144
    # nx varia con Y de pantalla (arr->abj):  16->96
    x = int((ny - 22)  * _W / (144 - 22))
    y = int((nx - 16)  * _H / (96  - 16))

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
        # Lectura cruda directa al chip
        rx = _touch.send_command(_touch.GET_X)
        ry = _touch.send_command(_touch.GET_Y)
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