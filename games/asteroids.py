"""
Juego 4: Asteroids Touch
Autor: [Asignar]

Mecanica:
  - Nave en centro, asteroides flotando que se fragmentan al recibir impacto.
  - Jugador 1: joystick 1 — rotar + empuje. Boton — disparar.
  - Sacudir el dispositivo activa el hiperespacio (posicion aleatoria).
  - Graficos vectoriales: poligonos rotados mediante trigonometria.
"""
from drivers import display  as drv_display
from drivers import buzzer   as drv_buzzer
from drivers import imu      as drv_imu
from drivers import storage  as drv_storage
from drivers.joystick import joy1
from utime import sleep_ms, ticks_ms, ticks_diff
from math import sin, cos
import random


JUEGO_ID = "asteroids"

# Constantes de fisicas
VEL_MAX_NAVE  = 6.0
FRICCION_NAVE = 0.98
VEL_BALA      = 8.0
MAX_BALAS     = 5
W_SCR         = 320
H_SCR         = 240

PUNTOS_NAVE = [(0, -8), (-6, 6), (0, 3), (6, 6)]

# ─── Matematica vectorial ─────────────────────────────────────

def _rotar_puntos(puntos, cx, cy, angulo_rad):
    """
    Rota una lista de puntos (x,y) alrededor del centro (cx,cy).
    """
    s, c = sin(angulo_rad), cos(angulo_rad)
    resultado = []
    for px, py in puntos:
        # Rotar respecto al origen 0,0 y luego trasladar
        resultado.append((cx + px * c - py * s,
                          cy + px * s + py * c))
    return resultado


def _dibujar_poligono(display, puntos, color):
    """
    Dibuja un poligono cerrado uniendo los puntos con lineas.
    """
    if len(puntos) < 2: return
    for i in range(len(puntos)):
        p1 = puntos[i]
        p2 = puntos[(i + 1) % len(puntos)]
        display.draw_line(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]), color)


# ─── Funciones de Entidades ──────────────────────────────────

def _crear_nave():
    return {
        "x": W_SCR / 2, "y": H_SCR / 2,
        "vx": 0.0,  "vy": 0.0,
        "angulo": 0.0,
        "vidas": 3,
        "invulnerable": 60,   # frames de invulnerabilidad
    }

def _crear_asteroide(x, y, tamano, vx=None, vy=None):
    """tamano: 3=grande, 2=mediano, 1=pequeno. Forma: cuadrado."""
    size = tamano * 6

    if vx is None:
        vx = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
        if abs(vx) < 0.3:
            vx = 0.3 if vx >= 0 else -0.3
    if vy is None:
        vy = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
        if abs(vy) < 0.3:
            vy = 0.3 if vy >= 0 else -0.3

    return {
        "x": float(x), "y": float(y),
        "vx": vx, "vy": vy,
        "tamano": tamano,
        "size": size,
    }

def _generar_asteroides(cantidad):
    asteroides = []
    for _ in range(cantidad):
        # Que no aparezcan justo en el centro donde esta la nave
        x = random.choice([random.randint(0, 100), random.randint(220, 320)])
        y = random.choice([random.randint(0, 80), random.randint(160, 240)])
        asteroides.append(_crear_asteroide(x, y, 3))
    return asteroides

def _hiperespacio(nave):
    """Teletransporta la nave a una posicion aleatoria."""
    nave["x"] = float(random.randint(20, 300))
    nave["y"] = float(random.randint(20, 220))
    nave["vx"] = 0.0
    nave["vy"] = 0.0
    drv_buzzer.tono(1200, 100)
    drv_buzzer.tono(800, 100)

def _disparar(nave, balas):
    if len(balas) < MAX_BALAS:
        s, c = sin(nave["angulo"]), cos(nave["angulo"])
        bx = nave["x"] + 8 * s
        by = nave["y"] - 8 * c
        bvx = VEL_BALA * s
        bvy = -VEL_BALA * c
        balas.append({"x": bx, "y": by, "vx": bvx, "vy": bvy, "vida": 35})
        drv_buzzer.sfx_disparo()

# ─── Bucle Principal ──────────────────────────────────────────

def jugar(display):
    from drivers.display import NEGRO, BLANCO, CYAN, ROJO, AMARILLO
    
    nave = _crear_nave()
    asteroides = _generar_asteroides(4)
    balas = []
    puntaje = 0
    nivel = 1
    
    btn_anterior = False
    
    # Pre-render
    display.clear()
    
    while nave["vidas"] > 0:
        t_inicio = ticks_ms()
        
        # 1. Entrada
        jx = joy1.x()
        jy = joy1.y()
        btn_actual = joy1.boton()
        
        # Rotar (Eje X)
        if abs(jx) > 0.1:
            nave["angulo"] += jx * 0.15
            
        # Empuje (Eje Y hacia arriba: valores negativos)
        if jy < -0.1:
            s, c = sin(nave["angulo"]), cos(nave["angulo"])
            # Invertimos el empuje porque empujamos hacia "arriba" relativo al angulo
            nave["vx"] += s * 0.4
            nave["vy"] -= c * 0.4
            
        # Limitar velocidad
        vel = (nave["vx"]**2 + nave["vy"]**2)**0.5
        if vel > VEL_MAX_NAVE:
            nave["vx"] = (nave["vx"] / vel) * VEL_MAX_NAVE
            nave["vy"] = (nave["vy"] / vel) * VEL_MAX_NAVE
            
        if btn_actual and not btn_anterior:
            _disparar(nave, balas)
        btn_anterior = btn_actual
            
        # Hiperespacio
        if drv_imu.sacudida(1.8):
            _hiperespacio(nave)
            
        # 2. Fisica
        nave["x"] = (nave["x"] + nave["vx"]) % W_SCR
        nave["y"] = (nave["y"] + nave["vy"]) % H_SCR
        nave["vx"] *= FRICCION_NAVE
        nave["vy"] *= FRICCION_NAVE
        
        if nave["invulnerable"] > 0:
            nave["invulnerable"] -= 1
            
        for b in balas:
            b["x"] = (b["x"] + b["vx"]) % W_SCR
            b["y"] = (b["y"] + b["vy"]) % H_SCR
            b["vida"] -= 1
        balas = [b for b in balas if b["vida"] > 0]
        
        for a in asteroides:
            a["x"] += a["vx"]
            a["y"] += a["vy"]
            s = a["size"]
            if a["x"] - s < 0:
                a["x"] = float(s)
                a["vx"] = abs(a["vx"])
            elif a["x"] + s > W_SCR:
                a["x"] = float(W_SCR - s)
                a["vx"] = -abs(a["vx"])
            if a["y"] - s < 0:
                a["y"] = float(s)
                a["vy"] = abs(a["vy"])
            elif a["y"] + s > H_SCR:
                a["y"] = float(H_SCR - s)
                a["vy"] = -abs(a["vy"])
            
        # 3. Colisiones
        nuevos_asteroides = []
        asteroides_destruidos = set()
        balas_destruidas = set()
        
        for i, a in enumerate(asteroides):
            # Proyectiles vs Asteroide
            for j, b in enumerate(balas):
                if j in balas_destruidas: continue
                s = a["size"]
                if abs(a["x"] - b["x"]) < s and abs(a["y"] - b["y"]) < s:
                    asteroides_destruidos.add(i)
                    balas_destruidas.add(j)
                    puntaje += 10 * a["tamano"]
                    drv_buzzer.sfx_explosion()
                    # Generar fragmentos
                    if a["tamano"] > 1:
                        nuevos_asteroides.append(_crear_asteroide(a["x"], a["y"], a["tamano"] - 1))
                        nuevos_asteroides.append(_crear_asteroide(a["x"], a["y"], a["tamano"] - 1))
                    break
                    
            # Nave vs Asteroide
            if nave["invulnerable"] == 0 and i not in asteroides_destruidos:
                s = a["size"] + 5
                if abs(a["x"] - nave["x"]) < s and abs(a["y"] - nave["y"]) < s:
                    nave["vidas"] -= 1
                    drv_buzzer.sfx_error()
                    nave["x"] = W_SCR / 2
                    nave["y"] = H_SCR / 2
                    nave["vx"] = 0
                    nave["vy"] = 0
                    nave["invulnerable"] = 60
        
        asteroides = [a for i, a in enumerate(asteroides) if i not in asteroides_destruidos]
        asteroides.extend(nuevos_asteroides)
        balas = [b for j, b in enumerate(balas) if j not in balas_destruidas]
        
        # Subir nivel
        if len(asteroides) == 0:
            nivel += 1
            asteroides = _generar_asteroides(3 + nivel)
            drv_buzzer.sfx_nivel_up()
            nave["invulnerable"] = 60
            
        # 4. Dibujar
        display.fill_rectangle(0, 0, W_SCR, H_SCR, NEGRO)
        
        # UI
        display.draw_text8x8(5, 5, f"Ptos:{puntaje}", BLANCO)
        display.draw_text8x8(W_SCR - 60, 5, f"Vidas:{nave['vidas']}", ROJO)
        
        for a in asteroides:
            s = a["size"]
            display.fill_hrect(int(a["x"]) - s, int(a["y"]) - s, s * 2, s * 2, CYAN)
            
        for b in balas:
            display.draw_pixel(int(b["x"]), int(b["y"]), BLANCO)
            display.draw_pixel(int(b["x"])+1, int(b["y"]), BLANCO)
            display.draw_pixel(int(b["x"]), int(b["y"])+1, BLANCO)
            display.draw_pixel(int(b["x"])+1, int(b["y"])+1, BLANCO)
            
        if nave["vidas"] > 0:
            if nave["invulnerable"] == 0 or (nave["invulnerable"] // 4) % 2 == 0:
                pts = _rotar_puntos(PUNTOS_NAVE, nave["x"], nave["y"], nave["angulo"])
                _dibujar_poligono(display, pts, BLANCO)
                # Dibujar propulsor si empuja
                if jy < -0.1:
                    pts_prop = [(0, 3), (-3, 6), (0, 8), (3, 6)]
                    pts_prop = _rotar_puntos(pts_prop, nave["x"], nave["y"], nave["angulo"])
                    _dibujar_poligono(display, pts_prop, ROJO)
                
        # Mantener FPS estables (~30 fps)
        t_fin = ticks_ms()
        tiempo_frame = ticks_diff(t_fin, t_inicio)
        if tiempo_frame < 33:
            sleep_ms(33 - tiempo_frame)
            
    # Game Over
    drv_buzzer.sfx_game_over()
    display.fill_rectangle(0, 0, W_SCR, H_SCR, NEGRO)
    display.draw_text8x8(W_SCR//2 - 40, H_SCR//2 - 20, "GAME OVER", ROJO)
    display.draw_text8x8(W_SCR//2 - 52, H_SCR//2 - 4,  f"Puntaje: {puntaje}", BLANCO)

    es_record = drv_storage.guardar_record(JUEGO_ID, puntaje)
    if es_record:
        display.draw_text8x8(W_SCR//2 - 40, H_SCR//2 + 12, "NUEVO RECORD!", AMARILLO)

    sleep_ms(3000)
    return puntaje
