"""
Juego 1: Simon Says Plus
Autor: Jesus Alfonso Morales Jaimes

Mecanica:
  - Pantalla landscape 320x240 dividida en 4 cuadrantes 160x120.
  - El sistema reproduce una secuencia que el jugador repite tocando los cuadrantes.
  - A partir de la ronda 2 se intercalan gestos de inclinacion (IMU).
  - Cada ronda correcta suma puntos y agrega un elemento a la secuencia.

Acciones:
  0=Rojo  1=Verde  2=Azul  3=Amarillo  4=Inclinar Izq  5=Inclinar Der

Hardware:
  - ILI9341 tactil (entrada + salida)
  - Buzzer (tono por accion)
  - MPU6050 (gestos a partir del nivel 5)
"""
import random
from drivers import display as drv_display
from drivers import touch   as drv_touch
from drivers import buzzer  as drv_buzzer
from drivers import imu     as drv_imu
from drivers import storage as drv_storage
from utime import sleep_ms, ticks_ms, ticks_diff


JUEGO_ID = "simon_says"

# Pantalla landscape
_W = 320
_H = 240

# (x, y, ancho, alto, color_normal, color_brillante)
CUADRANTES = [
    (0,   0,   160, 120, drv_display.color(180, 0,   0  ), drv_display.color(255, 120, 120)),  # 0 Rojo  sup-izq
    (160, 0,   160, 120, drv_display.color(0,   180, 0  ), drv_display.color(120, 255, 120)),  # 1 Verde sup-der
    (0,   120, 160, 120, drv_display.color(0,   60,  200), drv_display.color(120, 180, 255)),  # 2 Azul  inf-izq
    (160, 120, 160, 120, drv_display.color(220, 200, 0  ), drv_display.color(255, 255, 160)),  # 3 Amar. inf-der
]

# Umbrales / temporizacion
_UMBRAL_IMU       = 0.45   # g
_TIEMPO_RESPUESTA = 5000   # ms
_PAUSA_ENTRE_PASOS = 250   # ms entre pasos de la secuencia
_DESTELLO_MS      = 320    # ms iluminacion cuadrante


# ── Punto de entrada ──────────────────────────────────────────

def jugar(display):
    random.seed(ticks_ms())
    puntaje   = 0
    secuencia = []
    #Se inicializa la interfaz grafica
    _pantalla_inicio(display)
    sleep_ms(900)
    #Se dibujan los cuadrantes
    _dibujar_cuadrantes(display)
    sleep_ms(500)

    while True:
        # A) Agregar nuevo paso
        if len(secuencia) < 1:
            nuevo = random.randint(0, 3)        # ronda 1: solo colores
        else:
            # ronda 2+: 50% gesto, 50% color (antes era ~33% gesto con randint(0,5))
            if random.random() < 0.5:
                nuevo = random.randint(4, 5)    # gesto IMU (izq/der)
            else:
                nuevo = random.randint(0, 3)    # color
        secuencia.append(nuevo)
        sleep_ms(500)

        # B) Reproducir
        _reproducir_secuencia(display, secuencia)

        # C) Esperar respuesta jugador
        correcto = _esperar_input(display, secuencia)

        # D) Evaluar
        if not correcto:
            drv_buzzer.sfx_error()
            sleep_ms(250)
            drv_buzzer.sfx_game_over()
            break

        puntaje += len(secuencia) * 10
        _mostrar_puntaje(display, puntaje, len(secuencia))
        drv_buzzer.sfx_nivel_up()
        sleep_ms(500)
        _dibujar_cuadrantes(display)
        sleep_ms(400)

    drv_storage.guardar_record(JUEGO_ID, puntaje)
    return puntaje


# ── Interfaz grafica ──────────────────────────────────────────

def _pantalla_inicio(display):
    display.fill_rectangle(0, 0, _W, _H, drv_display.NEGRO)
    display.draw_text8x8( 80,  90, "SIMON SAYS PLUS", drv_display.AMARILLO)
    display.draw_text8x8( 96, 120, "Repite secuencia", drv_display.BLANCO)
    display.draw_text8x8( 60, 150, "Lvl 2+: inclina console", drv_display.GRIS)


def _dibujar_cuadrantes(display):
    for q in CUADRANTES:
        x, y, w, h, col, _ = q
        display.fill_rectangle(x, y, w, h, col)
    # Lineas separadoras finas
    display.fill_rectangle(159, 0, 2, _H, drv_display.NEGRO)
    display.fill_rectangle(0, 119, _W, 2, drv_display.NEGRO)


def _iluminar_accion(display, accion):
    if accion < 4:
        x, y, w, h, col_normal, col_bri = CUADRANTES[accion]
        drv_buzzer.sfx_simon(accion)
        display.fill_rectangle(x, y, w, h, col_bri)
        sleep_ms(_DESTELLO_MS)
        display.fill_rectangle(x, y, w, h, col_normal)
        # Restaurar separadores
        display.fill_rectangle(159, 0, 2, _H, drv_display.NEGRO)
        display.fill_rectangle(0, 119, _W, 2, drv_display.NEGRO)
    elif accion == 4:
        drv_buzzer.tono(1200, 150)
        _mostrar_gesto(display, "<-- IZQUIERDA")
    elif accion == 5:
        drv_buzzer.tono(1500, 150)
        _mostrar_gesto(display, "DERECHA  -->")


def _mostrar_gesto(display, texto):
    display.fill_rectangle(40, 95, 240, 50, drv_display.GRIS_OSC)
    display.draw_text8x8(80, 115, texto, drv_display.BLANCO)
    sleep_ms(650)
    _dibujar_cuadrantes(display)


def _mostrar_puntaje(display, puntaje, nivel):
    display.fill_rectangle(40, 100, 240, 40, drv_display.GRIS_OSC)
    display.draw_text8x8(70, 108, f"NIVEL {nivel} OK!", drv_display.AMARILLO)
    display.draw_text8x8(70, 124, f"PUNTOS: {puntaje}", drv_display.BLANCO)


def _reproducir_secuencia(display, secuencia):
    for accion in secuencia:
        _iluminar_accion(display, accion)
        sleep_ms(_PAUSA_ENTRE_PASOS)


# ── Lectura combinada (tactil + IMU) ──────────────────────────

def _obtener_accion_jugador():
    # 1. Tactil
    t = drv_touch.leer()
    if t is not None:
        x, y = t
        if x < 160 and y < 120:  return 0
        if x >= 160 and y < 120: return 1
        if x < 160 and y >= 120: return 2
        if x >= 160 and y >= 120: return 3

    # 2. IMU — el eje X del MPU6050 esta invertido respecto a la orientacion
    # fisica de la consola (verificado con test_imu.py: _INV_X = True),
    # por eso ax > 0 al inclinar a la IZQUIERDA y ax < 0 al inclinar a la DERECHA.
    ax, _, _ = drv_imu.leer()
    if ax >  _UMBRAL_IMU: return 4   # inclinacion izquierda
    if ax < -_UMBRAL_IMU: return 5   # inclinacion derecha

    return None


def _esperar_liberacion(max_ms=1500):
    """Bloquea hasta que el jugador suelte el toque y la consola vuelva a zona neutra.
    Evita que un gesto sostenido o dedo apoyado dispare el siguiente paso."""
    t_inicio = ticks_ms()
    neutro_g = _UMBRAL_IMU * 0.6
    while ticks_diff(ticks_ms(), t_inicio) < max_ms:
        t = drv_touch.leer()
        ax, _, _ = drv_imu.leer()
        if t is None and abs(ax) < neutro_g:
            return
        sleep_ms(15)


# ── Validacion de la respuesta ────────────────────────────────

def _esperar_input(display, secuencia):
    # Drenar estado residual antes de empezar (gesto sostenido del paso anterior, etc.)
    _esperar_liberacion(max_ms=100)

    for esperada in secuencia:
        t_inicio = ticks_ms()

        while True:
            accion = _obtener_accion_jugador()

            if accion is not None:
                # Si la accion esperada es color, ignorar gestos parasitos
                # (temblor leve del IMU mientras el jugador apunta al cuadrante).
                if esperada < 4 and accion >= 4:
                    sleep_ms(20)
                    if ticks_diff(ticks_ms(), t_inicio) > _TIEMPO_RESPUESTA:
                        return False
                    continue

                if accion == esperada:
                    _iluminar_accion(display, accion)
                    _esperar_liberacion()
                    break
                else:
                    return False

            if ticks_diff(ticks_ms(), t_inicio) > _TIEMPO_RESPUESTA:
                return False

            sleep_ms(15)
    return True
