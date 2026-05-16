"""
Juego 2: Gyro Maze
Autor: [Asignar]

Mecanica:
  - Laberinto en vista superior (landscape 320x240).
  - Pelota controlada inclinando la consola (MPU6050).
  - Objetivo: llegar a la meta (G) evitando los agujeros (H).
  - Cada nivel da puntos por completarlo + bonus por tiempo restante.
  - Game over si la pelota cae en un agujero o se acaba el tiempo.

Convencion de orientacion (consola landscape, mirando la pantalla):
  - Inclinar borde DERECHO  hacia abajo  -> pelota se mueve a la DERECHA
  - Inclinar borde IZQUIERDO hacia abajo -> pelota se mueve a la IZQUIERDA
  - Inclinar borde INFERIOR hacia abajo  -> pelota baja
  - Inclinar borde SUPERIOR hacia abajo  -> pelota sube
Este mapeo se validó con test_imu.py (_INV_X = True, _INV_Y = False).

Hardware:
  - MPU6050 (control principal)
  - ILI9341 (renderizado)
  - Buzzer (sfx)
  - Joystick (boton para calibrar al inicio)
"""
from drivers import display as drv_display
from drivers import imu     as drv_imu
from drivers import buzzer  as drv_buzzer
from drivers import storage as drv_storage
from drivers.joystick import joy1
from utime import sleep_ms, ticks_ms, ticks_diff

from drivers.display import (NEGRO, BLANCO, ROJO, VERDE,
                              AZUL, AMARILLO, CYAN, GRIS, GRIS_OSC)


JUEGO_ID = "gyro_maze"

# ── Dimensiones ───────────────────────────────────────────────
W_SCR = 320
H_SCR = 240
HUD_H = 16
CELDA = 16
COLS  = W_SCR // CELDA                # 20
FILAS = (H_SCR - HUD_H) // CELDA      # 14

# ── Pelota y fisica ───────────────────────────────────────────
RADIO    = 6
DAMP     = 0.92    # rozamiento (0..1, 1 = sin rozamiento)
ACCEL    = 0.60    # ganancia desde el IMU (g -> px/frame²)
MAX_VEL  = 4.0     # velocidad maxima por eje

# El IMU tiene el eje X invertido respecto a la orientacion fisica
# de la consola (verificado con test_imu.py -> _INV_X = True).
INV_X_IMU = True

# ── Tiempo ────────────────────────────────────────────────────
FPS_MS         = 33                   # ~30 fps
TIEMPO_NIVEL_S = 30                   # tiempo limite por nivel


# ── Niveles ───────────────────────────────────────────────────
# 20 columnas x 14 filas. Caracteres:
#   #=pared  .=pasillo  H=agujero  S=inicio  G=meta
_LEVELS = [
    [
        "####################",
        "#S.................#",
        "#..................#",
        "#......####........#",
        "#......#..#........#",
        "#......#..#........#",
        "#..........H.......#",
        "#..................#",
        "#........####......#",
        "#........#..#......#",
        "#........#..#......#",
        "#..................#",
        "#.................G#",
        "####################",
    ],
    [
        "####################",
        "#S....#............#",
        "#.....#....######..#",
        "#..........#.......#",
        "#######....#.####..#",
        "#..........#.#.....#",
        "#.H........#.#..H..#",
        "#..........#.#.....#",
        "#.####.....#.#######",
        "#.#........#.......#",
        "#.#......######....#",
        "#.#................#",
        "#.................G#",
        "####################",
    ],
    [
        "####################",
        "#S...#.........#...#",
        "#....#....H....#...#",
        "#....#.........#.H.#",
        "#....######.####...#",
        "#..................#",
        "#.####....H........#",
        "#....#....######...#",
        "#H...#.............#",
        "#....######.####...#",
        "#..................#",
        "#....#####.........#",
        "#....#............G#",
        "####################",
    ],
]


# ── Parsing del nivel ─────────────────────────────────────────

def _parse_level(rows):
    """Convierte la representacion textual en (matriz, start_px, goal_celda)."""
    assert len(rows) == FILAS, "El nivel debe tener {} filas".format(FILAS)
    matriz = []
    start  = (CELDA + CELDA // 2, HUD_H + CELDA + CELDA // 2)
    goal   = (COLS - 2, FILAS - 2)
    for r, row in enumerate(rows):
        assert len(row) == COLS, "Fila {} tiene {} cols (esperado {})".format(
            r, len(row), COLS)
        fila = []
        for c, ch in enumerate(row):
            if   ch == '#': fila.append(1)
            elif ch == 'H': fila.append(2)
            elif ch == 'G':
                fila.append(3)
                goal = (c, r)
            elif ch == 'S':
                fila.append(0)
                start = (c * CELDA + CELDA // 2,
                         HUD_H + r * CELDA + CELDA // 2)
            else:
                fila.append(0)
        matriz.append(fila)
    return matriz, start, goal


# ── Renderizado ───────────────────────────────────────────────

def _disco(display, cx, cy, r, col):
    """Disco lleno via scanlines (mas rapido que pixel a pixel)."""
    for dy in range(-r, r + 1):
        w = int((r * r - dy * dy) ** 0.5)
        if w > 0:
            display.fill_rectangle(cx - w, cy + dy, 2 * w, 1, col)


def _dibujar_celda(display, c, r, valor):
    x = c * CELDA
    y = HUD_H + r * CELDA
    if valor == 1:
        display.fill_rectangle(x, y, CELDA, CELDA, GRIS)
    elif valor == 2:
        _disco(display, x + CELDA // 2, y + CELDA // 2, CELDA // 2 - 1, ROJO)
        _disco(display, x + CELDA // 2, y + CELDA // 2, CELDA // 2 - 4, NEGRO)
    elif valor == 3:
        display.fill_rectangle(x + 2, y + 2, CELDA - 4, CELDA - 4, VERDE)
        display.draw_text8x8(x + 4, y + 4, "G", NEGRO)
    # valor 0 -> no dibuja nada (queda negro)


def _dibujar_nivel(display, matriz):
    display.fill_rectangle(0, HUD_H, W_SCR, H_SCR - HUD_H, NEGRO)
    for r in range(FILAS):
        for c in range(COLS):
            v = matriz[r][c]
            if v != 0:
                _dibujar_celda(display, c, r, v)


def _dibujar_pelota(display, x, y, col):
    _disco(display, int(x), int(y), RADIO, col)


def _borrar_pelota(display, x, y, matriz):
    """Limpia el bbox de la pelota y restaura las celdas que pisaba."""
    r  = RADIO + 1
    x0 = int(x) - r
    y0 = int(y) - r
    w  = 2 * r + 1
    display.fill_rectangle(x0, y0, w, w, NEGRO)

    # Restaurar celdas en el bounding box
    c0 = max(0, x0 // CELDA)
    c1 = min(COLS - 1, (x0 + w - 1) // CELDA)
    r0 = max(0, (y0 - HUD_H) // CELDA)
    r1 = min(FILAS - 1, (y0 + w - 1 - HUD_H) // CELDA)
    for rr in range(r0, r1 + 1):
        for cc in range(c0, c1 + 1):
            v = matriz[rr][cc]
            if v != 0:
                _dibujar_celda(display, cc, rr, v)


# ── Colisiones ────────────────────────────────────────────────

def _celda_en(matriz, x, y):
    """Devuelve el valor de la celda que contiene el centro (x, y)."""
    c = int(x // CELDA)
    r = int((y - HUD_H) // CELDA)
    if 0 <= c < COLS and 0 <= r < FILAS:
        return matriz[r][c]
    return 1


def _hay_pared(matriz, x, y, radio):
    """True si el cuadro (x±radio, y±radio) toca alguna pared."""
    c0 = int((x - radio) // CELDA)
    c1 = int((x + radio) // CELDA)
    r0 = int((y - radio - HUD_H) // CELDA)
    r1 = int((y + radio - HUD_H) // CELDA)
    for rr in range(r0, r1 + 1):
        for cc in range(c0, c1 + 1):
            if 0 <= cc < COLS and 0 <= rr < FILAS:
                if matriz[rr][cc] == 1:
                    return True
            else:
                return True  # fuera de la grilla = pared
    return False


# ── HUD ───────────────────────────────────────────────────────

def _hud(display, puntaje, nivel, segundos):
    display.fill_rectangle(0, 0, W_SCR, HUD_H, GRIS_OSC)
    display.draw_text8x8(  4, 4, "PTS:{}".format(puntaje),    BLANCO)
    display.draw_text8x8(120, 4, "LVL:{}".format(nivel),       AMARILLO)
    display.draw_text8x8(220, 4, "T:{:02d}s".format(max(0, segundos)), CYAN)


def _hud_tiempo(display, segundos):
    """Solo actualiza la parte del tiempo (evita parpadeo)."""
    display.fill_rectangle(215, 0, W_SCR - 215, HUD_H, GRIS_OSC)
    display.draw_text8x8(220, 4, "T:{:02d}s".format(max(0, segundos)), CYAN)


# ── Pantallas auxiliares ──────────────────────────────────────

def _pantalla_calibracion(display):
    display.fill_rectangle(0, 0, W_SCR, H_SCR, NEGRO)
    display.draw_text8x8(116,  50, "GYRO MAZE",        CYAN)
    display.draw_text8x8( 40,  90, "Apoya plano la consola", BLANCO)
    display.draw_text8x8( 40, 110, "y presiona el BOTON",     BLANCO)
    display.draw_text8x8( 40, 130, "para calibrar.",          GRIS)
    display.draw_text8x8( 40, 170, "Inclina para mover. Llega a la G.", GRIS)
    display.draw_text8x8( 40, 185, "Evita los agujeros rojos.",          GRIS)

    # Esperar pulsacion del boton
    while not joy1.boton():
        sleep_ms(20)

    display.fill_rectangle(40, 90, 240, 50, NEGRO)
    display.draw_text8x8(100, 110, "Calibrando...", AMARILLO)
    drv_imu.calibrar(muestras=80)
    drv_buzzer.sfx_seleccionar()

    # Esperar a que suelte para no disparar nada en el primer frame
    while joy1.boton():
        sleep_ms(20)
    sleep_ms(100)


def _pantalla_nivel_completo(display, nivel, puntaje):
    display.fill_rectangle(40, 80, 240, 80, GRIS_OSC)
    display.draw_text8x8(80, 100, "NIVEL {} OK!".format(nivel), AMARILLO)
    display.draw_text8x8(80, 120, "Puntos: {}".format(puntaje), BLANCO)
    sleep_ms(1200)


# ── Bucle de un nivel ─────────────────────────────────────────

def _jugar_nivel(display, rows_def, nivel_num, puntaje_acum):
    """Devuelve (puntaje_actualizado, gano_nivel)."""
    matriz, (px, py), _ = _parse_level(rows_def)

    _dibujar_nivel(display, matriz)
    _hud(display, puntaje_acum, nivel_num, TIEMPO_NIVEL_S)
    _dibujar_pelota(display, px, py, AMARILLO)
    sleep_ms(400)

    vx, vy = 0.0, 0.0
    t_inicio = ticks_ms()
    tiempo_restante_ms = TIEMPO_NIVEL_S * 1000
    ultimo_seg = TIEMPO_NIVEL_S
    prev_px, prev_py = px, py

    while True:
        t_frame = ticks_ms()

        # 1. Input IMU
        ax, ay, _ = drv_imu.leer()
        if INV_X_IMU:
            ax = -ax

        # 2. Integrar velocidad con rozamiento + clamp
        vx = vx * DAMP + ax * ACCEL
        vy = vy * DAMP + ay * ACCEL
        if vx >  MAX_VEL: vx =  MAX_VEL
        elif vx < -MAX_VEL: vx = -MAX_VEL
        if vy >  MAX_VEL: vy =  MAX_VEL
        elif vy < -MAX_VEL: vy = -MAX_VEL

        # 3. Mover y resolver colisiones eje por eje
        nx = px + vx
        if _hay_pared(matriz, nx, py, RADIO):
            nx = px
            vx = 0
        ny = py + vy
        if _hay_pared(matriz, nx, ny, RADIO):
            ny = py
            vy = 0
        px, py = nx, ny

        # 4. Evaluar celda actual (agujero / meta)
        v_centro = _celda_en(matriz, px, py)
        if v_centro == 2:
            # Cayo en agujero
            _borrar_pelota(display, prev_px, prev_py, matriz)
            drv_buzzer.sfx_error()
            drv_buzzer.sfx_explosion()
            return puntaje_acum, False
        if v_centro == 3:
            bonus = (tiempo_restante_ms // 1000) * 10
            drv_buzzer.sfx_nivel_up()
            return puntaje_acum + 100 + bonus, True

        # 5. Render dirty-rect de la pelota
        if int(px) != int(prev_px) or int(py) != int(prev_py):
            _borrar_pelota(display, prev_px, prev_py, matriz)
            _dibujar_pelota(display, px, py, AMARILLO)
            prev_px, prev_py = px, py

        # 6. Tiempo / HUD
        tiempo_restante_ms = TIEMPO_NIVEL_S * 1000 - ticks_diff(ticks_ms(), t_inicio)
        if tiempo_restante_ms <= 0:
            drv_buzzer.sfx_game_over()
            return puntaje_acum, False
        seg = tiempo_restante_ms // 1000
        if seg != ultimo_seg:
            _hud_tiempo(display, seg)
            ultimo_seg = seg

        # 7. FPS lock
        tiempo_frame = ticks_diff(ticks_ms(), t_frame)
        if tiempo_frame < FPS_MS:
            sleep_ms(FPS_MS - tiempo_frame)


# ── Entry point ───────────────────────────────────────────────

def jugar(display):
    """Punto de entrada del juego. Devuelve puntaje final."""
    _pantalla_calibracion(display)

    puntaje = 0
    nivel   = 1
    while True:
        idx = (nivel - 1) % len(_LEVELS)
        puntaje, gano = _jugar_nivel(display, _LEVELS[idx], nivel, puntaje)
        if not gano:
            break
        _pantalla_nivel_completo(display, nivel, puntaje)
        nivel += 1

    drv_storage.guardar_record(JUEGO_ID, puntaje)
    return puntaje
