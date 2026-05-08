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
_MIN_X = 200
_MAX_X = 3800
_MIN_Y = 300
_MAX_Y = 3700

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
    """
    Devuelve (x, y) en landscape (0-319, 0-239), o None.
    Hace muestreo con consenso (5 lecturas estables) — robusto frente a ruido.
    """
    if _touch is None or not hay_toque():
        return None

    # get_touch() bloquea hasta tener 5 muestras consistentes o timeout (~2s).
    # Si quieres una lectura no-bloqueante usa raw_touch() y normalize().
    p = _touch.get_touch()
    if p is None:
        return None

    nx, ny = p  # coordenadas en orientacion nativa (240x320)

    # Rotar a landscape: el panel nativo es portrait 240x320,
    # pero tu UI dibuja en 320x240. Mapeo estandar de rotacion 90°:
    #   x_landscape = ny
    #   y_landscape = (NATIVE_W - 1) - nx
    x = ny
    y = (_NATIVE_W - 1) - nx

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