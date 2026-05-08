"""
Juego 4: Asteroids Touch
Autor: [Asignar]

Mecanica:
  - Nave estatica en el centro de la pantalla, solo rota.
  - Rotacion mediante encoder rotativo KY-040 (joy1.boton aun dispara).
  - Asteroides cuadrados que rebotan en los bordes.
  - Renderizado dirty-rect: borra posicion previa y dibuja la nueva
    para evitar parpadeo (sin limpiar toda la pantalla cada frame).
"""
from drivers import display  as drv_display
from drivers import buzzer   as drv_buzzer
from drivers import storage  as drv_storage
from drivers.joystick import joy1
from drivers.encoder  import encoder1
from utime import sleep_ms, ticks_ms, ticks_diff
from math import sin, cos
import random


JUEGO_ID = "asteroids"

# Constantes
VEL_BALA  = 6.0
MAX_BALAS = 5
W_SCR     = 320
H_SCR     = 240
NAVE_X    = W_SCR // 2
NAVE_Y    = H_SCR // 2
FPS_MS    = 33  # ~30 fps

PUNTOS_NAVE = [(0, -8), (-6, 6), (0, 3), (6, 6)]

# ─── Geometria ────────────────────────────────────────────────

def _rotar_puntos(puntos, cx, cy, angulo_rad):
    s, c = sin(angulo_rad), cos(angulo_rad)
    return [(cx + px * c - py * s, cy + px * s + py * c) for px, py in puntos]


def _dibujar_poligono(display, puntos, color):
    if len(puntos) < 2:
        return
    n = len(puntos)
    for i in range(n):
        p1 = puntos[i]
        p2 = puntos[(i + 1) % n]
        display.draw_line(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]), color)


# ─── Entidades ────────────────────────────────────────────────

def _crear_nave():
    return {
        "x": float(NAVE_X), "y": float(NAVE_Y),
        "angulo": 0.0,
        "prev_pts": None,
        "vidas": 3,
        "invulnerable": 60,
    }


def _crear_asteroide(x, y, tamano, vx=None, vy=None):
    """tamano: 3=grande, 2=mediano, 1=pequeno. Cuadrado mas chico."""
    size = tamano * 4  # antes *6, mas chico para reducir parpadeo

    if vx is None:
        vx = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
        if abs(vx) < 0.4:
            vx = 0.4 if vx >= 0 else -0.4
    if vy is None:
        vy = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
        if abs(vy) < 0.4:
            vy = 0.4 if vy >= 0 else -0.4

    return {
        "x": float(x), "y": float(y),
        "prev_x": float(x), "prev_y": float(y),
        "vx": vx, "vy": vy,
        "tamano": tamano,
        "size": size,
    }


def _generar_asteroides(cantidad):
    asteroides = []
    for _ in range(cantidad):
        x = random.choice([random.randint(20, 100), random.randint(220, 300)])
        y = random.choice([random.randint(20, 80),  random.randint(160, 220)])
        asteroides.append(_crear_asteroide(x, y, 3))
    return asteroides


def _disparar(nave, balas):
    if len(balas) >= MAX_BALAS:
        return
    s, c = sin(nave["angulo"]), cos(nave["angulo"])
    bx = nave["x"] + 8 * s
    by = nave["y"] - 8 * c
    bvx =  VEL_BALA * s
    bvy = -VEL_BALA * c
    balas.append({
        "x": bx, "y": by,
        "prev_x": bx, "prev_y": by,
        "vx": bvx, "vy": bvy,
        "vida": 35,
    })
    drv_buzzer.sfx_disparo()


def _borrar_bala(display, b, color):
    x = int(b["prev_x"]); y = int(b["prev_y"])
    display.draw_pixel(x,     y,     color)
    display.draw_pixel(x + 1, y,     color)
    display.draw_pixel(x,     y + 1, color)
    display.draw_pixel(x + 1, y + 1, color)


def _dibujar_bala(display, b, color):
    x = int(b["x"]); y = int(b["y"])
    display.draw_pixel(x,     y,     color)
    display.draw_pixel(x + 1, y,     color)
    display.draw_pixel(x,     y + 1, color)
    display.draw_pixel(x + 1, y + 1, color)


# ─── Bucle principal ──────────────────────────────────────────

def jugar(display):
    from drivers.display import NEGRO, BLANCO, CYAN, ROJO, AMARILLO

    nave = _crear_nave()
    asteroides = _generar_asteroides(4)
    balas = []
    puntaje = 0
    nivel = 1
    btn_anterior = False
    prev_puntaje = -1
    prev_vidas   = -1

    display.clear()

    # Reset contador del encoder
    encoder1.delta()

    while nave["vidas"] > 0:
        t_inicio = ticks_ms()

        # 1. Entrada
        delta_enc  = encoder1.delta()
        btn_actual = joy1.boton() or encoder1.boton()

        if delta_enc != 0:
            nave["angulo"] += delta_enc * 0.2

        if btn_actual and not btn_anterior:
            _disparar(nave, balas)
        btn_anterior = btn_actual

        # 2. Fisica (solo asteroides y balas; nave estatica)
        if nave["invulnerable"] > 0:
            nave["invulnerable"] -= 1

        for b in balas:
            b["prev_x"] = b["x"]
            b["prev_y"] = b["y"]
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["vida"] -= 1
        balas_a_borrar = [b for b in balas if b["vida"] <= 0
                          or b["x"] < 0 or b["x"] >= W_SCR
                          or b["y"] < 0 or b["y"] >= H_SCR]
        for b in balas_a_borrar:
            _borrar_bala(display, {"prev_x": b["x"], "prev_y": b["y"]}, NEGRO)
            balas.remove(b)

        for a in asteroides:
            a["prev_x"] = a["x"]
            a["prev_y"] = a["y"]
            a["x"] += a["vx"]
            a["y"] += a["vy"]
            s = a["size"]
            if a["x"] - s < 0:
                a["x"] = float(s);          a["vx"] = abs(a["vx"])
            elif a["x"] + s > W_SCR:
                a["x"] = float(W_SCR - s);  a["vx"] = -abs(a["vx"])
            if a["y"] - s < 0:
                a["y"] = float(s);          a["vy"] = abs(a["vy"])
            elif a["y"] + s > H_SCR:
                a["y"] = float(H_SCR - s);  a["vy"] = -abs(a["vy"])

        # 3. Colisiones
        nuevos_asteroides = []
        asteroides_destruidos = set()
        balas_destruidas = set()

        for i, a in enumerate(asteroides):
            sa = a["size"]
            for j, b in enumerate(balas):
                if j in balas_destruidas:
                    continue
                if abs(a["x"] - b["x"]) < sa and abs(a["y"] - b["y"]) < sa:
                    asteroides_destruidos.add(i)
                    balas_destruidas.add(j)
                    puntaje += 10 * a["tamano"]
                    drv_buzzer.sfx_explosion()
                    if a["tamano"] > 1:
                        nuevos_asteroides.append(_crear_asteroide(a["x"], a["y"], a["tamano"] - 1))
                        nuevos_asteroides.append(_crear_asteroide(a["x"], a["y"], a["tamano"] - 1))
                    break

            if nave["invulnerable"] == 0 and i not in asteroides_destruidos:
                d = a["size"] + 5
                if abs(a["x"] - nave["x"]) < d and abs(a["y"] - nave["y"]) < d:
                    nave["vidas"] -= 1
                    drv_buzzer.sfx_error()
                    nave["invulnerable"] = 60

        # Borrar asteroides destruidos de pantalla
        for i in asteroides_destruidos:
            a = asteroides[i]
            s = a["size"]
            display.fill_hrect(int(a["x"]) - s, int(a["y"]) - s, s * 2, s * 2, NEGRO)
        # Borrar balas destruidas de pantalla
        for j in balas_destruidas:
            b = balas[j]
            _borrar_bala(display, {"prev_x": b["x"], "prev_y": b["y"]}, NEGRO)

        asteroides = [a for i, a in enumerate(asteroides) if i not in asteroides_destruidos]
        asteroides.extend(nuevos_asteroides)
        balas      = [b for j, b in enumerate(balas)      if j not in balas_destruidas]

        # Subir nivel
        if len(asteroides) == 0:
            nivel += 1
            asteroides = _generar_asteroides(3 + nivel)
            drv_buzzer.sfx_nivel_up()
            nave["invulnerable"] = 60

        # 4. Dibujar (dirty-rect)

        # Asteroides: borrar prev, dibujar nuevo
        for a in asteroides:
            s = a["size"]
            display.fill_hrect(int(a["prev_x"]) - s, int(a["prev_y"]) - s,
                               s * 2, s * 2, NEGRO)
            display.fill_hrect(int(a["x"]) - s, int(a["y"]) - s,
                               s * 2, s * 2, CYAN)

        # Balas: borrar prev, dibujar nuevo
        for b in balas:
            _borrar_bala(display, b, NEGRO)
            _dibujar_bala(display, b, BLANCO)

        # Nave: borrar polygon previo (si existe), dibujar nuevo
        if nave["prev_pts"] is not None:
            _dibujar_poligono(display, nave["prev_pts"], NEGRO)
        visible = (nave["invulnerable"] == 0
                   or (nave["invulnerable"] // 4) % 2 == 0)
        if visible:
            pts = _rotar_puntos(PUNTOS_NAVE, nave["x"], nave["y"], nave["angulo"])
            _dibujar_poligono(display, pts, BLANCO)
            nave["prev_pts"] = pts
        else:
            nave["prev_pts"] = None

        # UI: solo redibujar si cambio
        if puntaje != prev_puntaje:
            display.fill_hrect(5, 5, 90, 8, NEGRO)
            display.draw_text8x8(5, 5, "Ptos:{}".format(puntaje), BLANCO)
            prev_puntaje = puntaje
        if nave["vidas"] != prev_vidas:
            display.fill_hrect(W_SCR - 70, 5, 70, 8, NEGRO)
            display.draw_text8x8(W_SCR - 60, 5, "Vidas:{}".format(nave["vidas"]), ROJO)
            prev_vidas = nave["vidas"]

        # 5. FPS lock
        tiempo_frame = ticks_diff(ticks_ms(), t_inicio)
        if tiempo_frame < FPS_MS:
            sleep_ms(FPS_MS - tiempo_frame)

    # Game Over
    drv_buzzer.sfx_game_over()
    display.fill_rectangle(0, 0, W_SCR, H_SCR, NEGRO)
    display.draw_text8x8(W_SCR // 2 - 40, H_SCR // 2 - 20, "GAME OVER",   ROJO)
    display.draw_text8x8(W_SCR // 2 - 52, H_SCR // 2 - 4,
                         "Puntaje: {}".format(puntaje), BLANCO)

    if drv_storage.guardar_record(JUEGO_ID, puntaje):
        display.draw_text8x8(W_SCR // 2 - 52, H_SCR // 2 + 12,
                             "NUEVO RECORD!", AMARILLO)

    sleep_ms(3000)
    return puntaje
