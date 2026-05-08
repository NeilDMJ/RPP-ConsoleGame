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
from math import sin, cos, pi
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
    """tamano: 3=grande, 2=mediano, 1=pequeno."""
    puntos_base = []
    num_puntos = 5 + tamano * 2
    radio = tamano * 6.0
    for i in range(num_puntos):
        angulo = (2 * pi / num_puntos) * i
        r = radio + random.uniform(-radio*0.3, radio*0.3)
        puntos_base.append((r * cos(angulo), r * sin(angulo)))
        
    if vx is None:
        vx = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
    if vy is None:
        vy = random.uniform(-1.0, 1.0) * (4 - tamano) * 0.6
        
    return {
        "x": float(x), "y": float(y),
        "vx": vx, "vy": vy,
        "tamano": tamano,
        "radio": radio, # para colisiones
        "puntos_base": puntos_base,
        "angulo": 0.0,
        "rotacion": random.uniform(-0.1, 0.1)
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
    from drivers.display import NEGRO, BLANCO, CYAN, ROJO
    
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
            a["x"] = (a["x"] + a["vx"]) % W_SCR
            a["y"] = (a["y"] + a["vy"]) % H_SCR
            a["angulo"] += a["rotacion"]
            
        # 3. Colisiones
        nuevos_asteroides = []
        asteroides_destruidos = set()
        balas_destruidas = set()
        
        for i, a in enumerate(asteroides):
            # Proyectiles vs Asteroide
            for j, b in enumerate(balas):
                if j in balas_destruidas: continue
                dist_sq = (a["x"] - b["x"])**2 + (a["y"] - b["y"])**2
                if dist_sq < a["radio"]**2 * 1.5: # 1.5 aprox padding
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
                dist_sq = (a["x"] - nave["x"])**2 + (a["y"] - nave["y"])**2
                if dist_sq < (a["radio"] + 5)**2:
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
            pts = _rotar_puntos(a["puntos_base"], a["x"], a["y"], a["angulo"])
            _dibujar_poligono(display, pts, CYAN)
            
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
            
    return puntaje
