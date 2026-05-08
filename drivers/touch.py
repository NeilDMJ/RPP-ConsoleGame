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

# ── Calibracion ───────────────────────────────────────────────
# nx = lectura cruda GET_X del XPT2046 (eje vertical landscape)
# ny = lectura cruda GET_Y del XPT2046 (eje horizontal landscape)
# Valores impresos por calibrar()
_MIN_NX = 225
_MAX_NX = 1767
_MIN_NY = 297
_MAX_NY = 1871

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
        x_min=_MIN_NX, x_max=_MAX_NX,
        y_min=_MIN_NY, y_max=_MAX_NY,
    )


def hay_toque():
    """Consulta rapida del pin PENIRQ. True si hay dedo apoyado."""
    return _irq is not None and _irq.value() == 0


def leer():
    if _touch is None or not hay_toque():
        return None

    # raw_touch devuelve (GET_X, GET_Y) crudos validados contra rango.
    # Evitamos get_touch porque su normalize re-escala y romperia la rotacion.
    p = _touch.raw_touch()
    if p is None:
        return None

    nx, ny = p

    # Rotacion a landscape: x landscape <- ny, y landscape <- nx
    x = int((ny - _MIN_NY) * _W / (_MAX_NY - _MIN_NY))
    y = int((nx - _MIN_NX) * _H / (_MAX_NX - _MIN_NX))

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
    print(f"_MIN_NX = {min(xs)}")
    print(f"_MAX_NX = {max(xs)}")
    print(f"_MIN_NY = {min(ys)}")
    print(f"_MAX_NY = {max(ys)}")