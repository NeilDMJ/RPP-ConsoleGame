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

# ── Helpers de dibujo rapido ──────────────────────────────────

def _fila_juego(display, idx, sel):
    """
    Dibuja UNA fila del menu. Solo se llama cuando esa fila cambia.
    Landscape: 320x240. Cada fila ocupa 52px de alto, desde y=40.
    """
    j      = JUEGOS[idx]
    y      = 40 + idx * 50
    activo = idx == sel

    # Fondo de la fila (un solo fill_rectangle)
    bg = j["color"] if activo else GRIS_OSC
    display.fill_rectangle(8, y, W - 16, 46, bg)

    # Textos (3 llamadas draw_text8x8)
    tx = NEGRO if activo else BLANCO
    ts = NEGRO if activo else GRIS
    display.draw_text8x8(16, y + 6,  j["nombre"], tx)
    display.draw_text8x8(16, y + 20, j["sub"],    ts)

    rec = drv_storage.obtener_record(j["id"])
    display.draw_text8x8(16, y + 34, f"REC: {rec['record']}", ts)


def _dibujar_menu_completo(display, sel):
    """Dibuja el menu entero. Solo se llama al entrar al menu."""
    display.fill_rectangle(0, 0, W, H, NEGRO)
    # Cabecera
    display.fill_rectangle(0, 0, W, 36, color565(20, 20, 60))
    display.draw_text8x8(100, 14, "PICO  GAMES", BLANCO)
    # Todas las filas
    for i in range(len(JUEGOS)):
        _fila_juego(display, i, sel)
    # Pie
    display.fill_rectangle(0, H - 18, W, 18, color565(20, 20, 60))
    display.draw_text8x8(60, H - 12, "JOY=NAV   BTN=JUGAR", GRIS)


def _menu(display):
    sel         = 0
    sel_anterior = -1
    t_ultimo    = ticks_ms()
    btn_anterior = False

    _dibujar_menu_completo(display, sel)
    sel_anterior = sel

    while True:
        sleep_ms(60)

        ahora = ticks_ms()
        if ticks_diff(ahora, t_ultimo) > 200:
            d = joy1.direccion(umbral=0.7)
            if d == "arr":
                sel = (sel - 1) % len(JUEGOS)
                t_ultimo = ahora
            elif d == "abj":
                sel = (sel + 1) % len(JUEGOS)
                t_ultimo = ahora

        # Redibujar solo las dos filas que cambiaron
        if sel != sel_anterior:
            drv_buzzer.sfx_menu()
            _fila_juego(display, sel_anterior, sel)  # deseleccionar anterior
            _fila_juego(display, sel,          sel)  # seleccionar nueva
            sel_anterior = sel

        btn = joy1.boton()
        if btn and not btn_anterior:
            drv_buzzer.sfx_seleccionar()
            sleep_ms(100)
            return sel
        btn_anterior = btn


def _pantalla_game_over(display, idx, puntaje):
    j = JUEGOS[idx]
    display.fill_rectangle(0, 0, W, H, NEGRO)
    display.draw_text8x8(100, 60,  "GAME OVER",    ROJO)
    display.draw_text8x8(80,  90,  j["nombre"],    j["color"])
    display.draw_text8x8(80,  120, f"SCORE: {puntaje}", BLANCO)
    rec = drv_storage.obtener_record(j["id"])
    if puntaje >= rec["record"] and puntaje > 0:
        display.draw_text8x8(80, 150, "NUEVO RECORD!", AMARILLO)
    else:
        display.draw_text8x8(80, 150, f"REC:  {rec['record']}", GRIS)
    display.draw_text8x8(70, 200, "BTN para volver", GRIS)
    sleep_ms(800)
    while not joy1.boton():
        sleep_ms(50)
    sleep_ms(200)


# ── Inicializacion ────────────────────────────────────────────
display = drv_display.init_display()
drv_touch.init_touch()
drv_buzzer.init_buzzer()
drv_imu.init_imu()

# Splash
display.fill_rectangle(0, 0, W, H, color565(10, 10, 40))
display.draw_text8x8(100, 100, "PICO  GAMES", BLANCO)
display.draw_text8x8(110, 120, "Iniciando...", GRIS)
drv_buzzer.sfx_nivel_up()
sleep_ms(1000)

# ── Loop principal ────────────────────────────────────────────
while True:
    idx = _menu(display)

    # Transicion al juego
    display.fill_rectangle(0, 0, W, H, NEGRO)
    display.draw_text8x8(100, 110, JUEGOS[idx]["nombre"], JUEGOS[idx]["color"])
    sleep_ms(500)

    puntaje = JUEGOS[idx]["modulo"].jugar(display)

    drv_storage.guardar_record(JUEGOS[idx]["id"], puntaje)
    _pantalla_game_over(display, idx, puntaje)
