"""
main.py — Consola de videojuegos Pico W
Orientacion horizontal (landscape) 320x240
"""

from drivers import display  as drv_display
from drivers import touch    as drv_touch
from drivers import buzzer   as drv_buzzer
from drivers import imu      as drv_imu
from drivers import storage  as drv_storage
from drivers.joystick import joy1

from games import simon_says
from games import gyro_maze
from games import tank_wars
from games import asteroids

from utime import sleep_ms, ticks_ms, ticks_diff
from ili9341 import color565

# Dimensiones landscape
W = 320
H = 240

from drivers.display import (NEGRO, BLANCO, ROJO, VERDE,
                              AZUL, AMARILLO, CYAN, GRIS, GRIS_OSC)

JUEGOS = [
    {"nombre": "SIMON SAYS+",  "sub": "Memoria y tacto",    "modulo": simon_says, "color": AMARILLO, "id": "simon_says"},
    {"nombre": "GYRO MAZE",    "sub": "Laberinto inercial", "modulo": gyro_maze,  "color": CYAN,     "id": "gyro_maze"},
    {"nombre": "TANK WARS",    "sub": "2 jugadores",        "modulo": tank_wars,  "color": ROJO,     "id": "tank_wars"},
    {"nombre": "ASTEROIDS",    "sub": "Modo cooperativo",   "modulo": asteroids,  "color": VERDE,    "id": "asteroids"},
]

# ── Helpers de dibujo ─────────────────────────────────────────

def _fila_juego(display, idx, sel):
    j      = JUEGOS[idx]
    y      = 40 + idx * 50
    activo = idx == sel

    # Fondo siempre oscuro
    display.fill_rectangle(8, y, W - 16, 46, GRIS_OSC)

    # Borde: solo si esta seleccionado, grosor 3px
    if activo:
        display.draw_rectangle(8,     y,     W - 16, 46, j["color"])
        display.draw_rectangle(9,     y + 1, W - 18, 44, j["color"])
        display.draw_rectangle(10,    y + 2, W - 20, 42, j["color"])

    # Textos — color del juego para el nombre si esta activo
    tx = j["color"] if activo else BLANCO
    ts = BLANCO     if activo else GRIS
    display.draw_text8x8(16, y + 6,  j["nombre"], tx)
    display.draw_text8x8(16, y + 20, j["sub"],    ts)

    rec = drv_storage.obtener_record(j["id"])
    display.draw_text8x8(16, y + 34, f"REC: {rec['record']}", ts)


def _dibujar_menu_completo(display, sel):
    display.fill_rectangle(0, 0, W, H, NEGRO)
    display.fill_rectangle(0, 0, W, 36, color565(20, 20, 60))
    display.draw_text8x8(100, 14, "PICO  GAMES", BLANCO)
    for i in range(len(JUEGOS)):
        _fila_juego(display, i, sel)
    display.fill_rectangle(0, H - 18, W, 18, color565(20, 20, 60))
    display.draw_text8x8(40, H - 12, "JOY=NAVEGAR   BTN=INICIAR JUEGO", GRIS)


def _leer_boton():
    """
    Lee el boton del joystick.
    KY-023: al presionar el SW conecta a GND -> lee 0 con PULL_UP
                                              -> lee 1 con PULL_DOWN
    Cambia 'not' por '' segun tu cableado si el boton no responde.
    """
    return joy1.boton()   # PULL_UP: presionado = 0 -> invertir a True
    # return joy1.boton()     # PULL_DOWN: presionado = 1 -> usar directo


def _esperar_boton_suelto():
    """Espera a que el boton se suelte para evitar activaciones dobles."""
    while _leer_boton():
        sleep_ms(20)
    sleep_ms(30)  # debounce


# ── Menu ──────────────────────────────────────────────────────

def _menu(display):
    sel          = 0
    sel_anterior = -1
    t_ultimo     = ticks_ms()
    btn_anterior = False

    _dibujar_menu_completo(display, sel)
    sel_anterior = sel

    while True:
        sleep_ms(50)

        # ── Navegacion con joystick ───────────────────────────
        ahora = ticks_ms()
        if ticks_diff(ahora, t_ultimo) > 200:
            d = joy1.direccion(umbral=0.7)
            if d == "arr":
                sel      = (sel - 1) % len(JUEGOS)
                t_ultimo = ahora
            elif d == "abj":
                sel      = (sel + 1) % len(JUEGOS)
                t_ultimo = ahora

        # Redibujar solo las filas que cambiaron
        if sel != sel_anterior:
            drv_buzzer.sfx_menu()
            _fila_juego(display, sel_anterior, sel)
            _fila_juego(display, sel,          sel)
            sel_anterior = sel

        # ── Boton: iniciar juego seleccionado ─────────────────
        btn_actual = _leer_boton()
        if btn_actual and not btn_anterior:
            # Feedback visual: parpadeo de la fila seleccionada
            for _ in range(2):
                display.fill_rectangle(8, 40 + sel * 50, W - 16, 46, BLANCO)
                sleep_ms(60)
                _fila_juego(display, sel, sel)
                sleep_ms(60)
            drv_buzzer.sfx_seleccionar()
            _esperar_boton_suelto()
            return sel

        btn_anterior = btn_actual 


# ── Pantallas de transicion ───────────────────────────────────

def _pantalla_iniciando(display, idx):
    """Pantalla de transicion antes de lanzar el juego."""
    j = JUEGOS[idx]
    display.fill_rectangle(0, 0, W, H, NEGRO)
    # Barra de color del juego arriba y abajo
    display.fill_rectangle(0, 0,      W, 8,  j["color"])
    display.fill_rectangle(0, H - 8,  W, 8,  j["color"])
    # Nombre del juego centrado
    display.draw_text8x8(80, 100, j["nombre"], j["color"])
    display.draw_text8x8(110, 120, j["sub"],   GRIS)
    display.draw_text8x8(100, 150, "INICIANDO...", BLANCO)
    sleep_ms(700)


def _pantalla_game_over(display, idx, puntaje):
    j = JUEGOS[idx]
    display.fill_rectangle(0, 0, W, H, NEGRO)
    display.fill_rectangle(0, 0, W, 8, ROJO)
    display.draw_text8x8(110, 40,  "GAME OVER",         ROJO)
    display.draw_text8x8(90,  70,  j["nombre"],         j["color"])
    display.draw_text8x8(90,  100, f"SCORE:  {puntaje}", BLANCO)

    rec = drv_storage.obtener_record(j["id"])
    if puntaje > 0 and puntaje >= rec["record"]:
        display.draw_text8x8(80, 130, "!! NUEVO RECORD !!", AMARILLO)
    else:
        display.draw_text8x8(90, 130, f"RECORD: {rec['record']}", GRIS)

    display.draw_text8x8(70, 180, "Presiona BTN para", GRIS)
    display.draw_text8x8(90, 195, "volver al menu",    GRIS)

    sleep_ms(600)
    _esperar_boton_suelto()         # por si el boton quedo presionado
    while not _leer_boton():
        sleep_ms(40)
    _esperar_boton_suelto()


# ── Inicializacion del hardware ───────────────────────────────

display = drv_display.init_display()
drv_touch.init_touch()           # descomentar cuando conectes el touch
drv_buzzer.init_buzzer()
drv_imu.init_imu()

# Splash de arranque
display.fill_rectangle(0, 0, W, H, color565(10, 10, 40))
display.fill_rectangle(0, 0, W, 4, CYAN)
display.fill_rectangle(0, H - 4, W, 4, CYAN)
display.draw_text8x8(100, 95,  "PICO  GAMES",  BLANCO)
display.draw_text8x8(105, 115, "Iniciando...", GRIS)
drv_buzzer.sfx_nivel_up()
sleep_ms(1200)

# ── Loop principal ────────────────────────────────────────────
while True:
    idx = _menu(display)
    _pantalla_iniciando(display, idx)

    puntaje = JUEGOS[idx]["modulo"].jugar(display)

    drv_storage.guardar_record(JUEGOS[idx]["id"], puntaje)
    _pantalla_game_over(display, idx, puntaje)