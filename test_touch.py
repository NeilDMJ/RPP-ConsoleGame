"""
test_touch.py — Prueba paso-a-paso la pipeline tactil de Simon Says.

Capas evaluadas en cada toque:
  1. PENIRQ          (drv_touch.hay_toque)
  2. raw_touch       (lectura cruda + filtro de calibracion del XPT2046)
  3. leer()          (coordenadas landscape 0-319, 0-239)
  4. Cuadrante       (misma logica que _obtener_accion_jugador)

Como usar:
  - Copiar este archivo a la Pico junto a main.py.
  - Desde el REPL: import test_touch
  - Toca cada cuadrante y observa la salida en consola + overlay.

Nombres de cuadrantes:
  0=ROJO sup-izq   1=VERDE sup-der   2=AZUL inf-izq   3=AMARILLO inf-der
"""
from drivers import display as drv_display
from drivers import touch   as drv_touch
from utime import sleep_ms, ticks_ms, ticks_diff


_W = 320
_H = 240

_NOMBRES = {0: "ROJO", 1: "VERDE", 2: "AZUL", 3: "AMARILLO", None: "----"}

CUADRANTES = [
    (0,   0,   160, 120, drv_display.color(180, 0,   0  )),
    (160, 0,   160, 120, drv_display.color(0,   180, 0  )),
    (0,   120, 160, 120, drv_display.color(0,   60,  200)),
    (160, 120, 160, 120, drv_display.color(220, 200, 0  )),
]


def _dibujar_cuadrantes(display):
    for x, y, w, h, col in CUADRANTES:
        display.fill_rectangle(x, y, w, h, col)
    display.fill_rectangle(159, 0, 2, _H, drv_display.NEGRO)
    display.fill_rectangle(0, 119, _W, 2, drv_display.NEGRO)


def _cuadrante_de(x, y):
    """Replica exacta de la decision de _obtener_accion_jugador."""
    if x < 160 and y < 120:  return 0
    if x >= 160 and y < 120: return 1
    if x < 160 and y >= 120: return 2
    if x >= 160 and y >= 120: return 3
    return None


def _hud(display, linea1, linea2):
    """Banda inferior con info de la ultima muestra."""
    display.fill_rectangle(0, 215, _W, 25, drv_display.NEGRO)
    display.draw_text8x8(2, 218, linea1[:39], drv_display.BLANCO)
    display.draw_text8x8(2, 228, linea2[:39], drv_display.AMARILLO)


def correr(display=None, duracion_ms=60_000):
    """Ejecuta el test interactivo durante `duracion_ms`."""
    if display is None:
        display = drv_display.init_display()
        drv_touch.init_touch()

    _dibujar_cuadrantes(display)
    _hud(display, "Toca cuadrantes. Mira REPL.", "")

    print("=" * 56)
    print("test_touch: pipeline Simon Says")
    print("Calibracion en uso:")
    print("  _MIN_NX={}  _MAX_NX={}".format(drv_touch._MIN_NX, drv_touch._MAX_NX))
    print("  _MIN_NY={}  _MAX_NY={}".format(drv_touch._MIN_NY, drv_touch._MAX_NY))
    print("=" * 56)
    print("Cap1 PENIRQ | Cap2 raw_touch (nx,ny) | Cap3 leer (x,y) | Cap4 cuadrante")
    print("-" * 56)

    t_inicio = ticks_ms()
    ultimo_print = 0
    rebote_ms = 80   # evita spam de la misma muestra

    while ticks_diff(ticks_ms(), t_inicio) < duracion_ms:
        ahora = ticks_ms()

        # Capa 1: PENIRQ
        irq = drv_touch.hay_toque()

        if not irq:
            sleep_ms(15)
            continue

        if ticks_diff(ahora, ultimo_print) < rebote_ms:
            sleep_ms(15)
            continue
        ultimo_print = ahora

        # Capa 2: raw_touch (sin normalizar). Bypass de hay_toque.
        raw = drv_touch._touch.raw_touch() if drv_touch._touch else None

        # Capa 3: leer() — pipeline real que ve el juego
        leido = drv_touch.leer()

        # Capa 4: decision cuadrante
        cuad = None
        if leido is not None:
            x, y = leido
            cuad = _cuadrante_de(x, y)

        # Tambien probemos send_command crudo para detectar drops del filtro
        crudo = None
        if drv_touch._touch is not None:
            try:
                rx = drv_touch._touch.send_command(drv_touch._touch.GET_X)
                ry = drv_touch._touch.send_command(drv_touch._touch.GET_Y)
                crudo = (rx, ry)
            except Exception as e:
                crudo = "ERR {}".format(e)

        nombre = _NOMBRES.get(cuad, "?")
        print("IRQ={} | crudo={} | raw={} | leer={} | cuad={} {}".format(
            int(irq), crudo, raw, leido, cuad, nombre))

        # HUD en pantalla
        l1 = "raw={} leer={}".format(raw, leido)
        l2 = "cuadrante={} {}".format(cuad, nombre)
        _hud(display, l1, l2)

        sleep_ms(15)

    print("-" * 56)
    print("Fin test_touch.")


# Auto-ejecutar al importar
if __name__ != "__main__":
    try:
        correr()
    except KeyboardInterrupt:
        print("Interrumpido.")
