"""
test_imu.py — Prueba paso-a-paso del MPU6050 y su orientacion en la consola.

Capas evaluadas:
  1. Lectura cruda del acelerometro (a.x, a.y, a.z en g, sin filtro)
  2. Lectura calibrada + filtrada (drv_imu.leer)
  3. Angulos pitch / roll derivados del vector gravedad
  4. Mapeo a "burbuja de nivel" en pantalla (320x240 landscape)

Como usar:
  - Copiar este archivo a la Pico junto a main.py.
  - Apoyar la consola plana, con pantalla viendo hacia arriba.
  - Desde el REPL: import test_imu
  - Inclina la consola en cada direccion y compara con el indicador.

Convencion de orientacion (consola landscape, mirando la pantalla):
  - Inclinar el borde DERECHO hacia abajo  -> burbuja se mueve a la DERECHA
  - Inclinar el borde IZQUIERDO hacia abajo -> burbuja se mueve a la IZQUIERDA
  - Inclinar el borde SUPERIOR hacia abajo -> burbuja se mueve hacia ARRIBA
  - Inclinar el borde INFERIOR hacia abajo -> burbuja se mueve hacia ABAJO

Si el mapeo no concuerda con la fisica, ajusta _INV_X / _INV_Y o _SWAP_XY
mas abajo. Esos son los unicos parametros que dependen del montaje del IMU.
"""
from drivers import display as drv_display
from drivers import imu     as drv_imu
from drivers import buzzer  as drv_buzzer
from drivers.joystick import joy1
from utime import sleep_ms, ticks_ms, ticks_diff
from math import atan2, sqrt, pi


_W = 320
_H = 240

# ── Ajustes de mapeo IMU -> pantalla ──────────────────────────
# Cambiar segun como este soldado el MPU6050 en la PCB.
_SWAP_XY = False   # True si los ejes X/Y del IMU estan girados 90 grados
_INV_X   = True   # True si inclinar a la derecha mueve la burbuja a la izquierda
_INV_Y   = False   # True si inclinar hacia adelante mueve la burbuja hacia abajo

# Sensibilidad: cuantos pixeles equivalen a 1g de inclinacion
_SENS_PX = 110

# Zona muerta visual (no mover la burbuja si la inclinacion es minima)
_DEAD_G  = 0.03


# ── Helpers de dibujo ─────────────────────────────────────────

def _dibujar_marco(display):
    display.fill_rectangle(0, 0, _W, _H, drv_display.NEGRO)

    # Titulo
    display.fill_rectangle(0, 0, _W, 16, drv_display.color(20, 20, 60))
    display.draw_text8x8(80, 4, "TEST IMU - NIVEL", drv_display.BLANCO)

    # Cruz central de referencia (centro de la pantalla)
    cx, cy = _W // 2, _H // 2
    display.fill_rectangle(cx - 40, cy,     80, 1, drv_display.GRIS)
    display.fill_rectangle(cx,     cy - 30, 1,  60, drv_display.GRIS)
    # Circulo objetivo (zona "nivelado")
    _circulo(display, cx, cy, 12, drv_display.GRIS)

    # Banda inferior para HUD (texto)
    display.fill_rectangle(0, _H - 48, _W, 48, drv_display.color(20, 20, 60))


def _circulo(display, cx, cy, r, col):
    """Dibuja un circulo por puntos (sencillo y suficiente para HUD)."""
    # Algoritmo de Bresenham simplificado
    x = r
    y = 0
    err = 0
    while x >= y:
        for dx, dy in ((x, y), (y, x), (-x, y), (-y, x),
                       (-x, -y), (-y, -x), (x, -y), (y, -x)):
            display.draw_pixel(cx + dx, cy + dy, col)
        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1


def _hud(display, l1, l2, l3):
    display.fill_rectangle(0, _H - 48, _W, 48, drv_display.color(20, 20, 60))
    if l1:
        display.draw_text8x8(2, _H - 44, l1[:39], drv_display.BLANCO)
    if l2:
        display.draw_text8x8(2, _H - 30, l2[:39], drv_display.AMARILLO)
    if l3:
        display.draw_text8x8(2, _H - 16, l3[:39], drv_display.CYAN)


def _burbuja(display, x, y, col):
    """Dibuja la burbuja (disco lleno) en (x, y)."""
    r = 8
    for dy in range(-r, r + 1):
        ancho = int((r * r - dy * dy) ** 0.5)
        if ancho > 0:
            display.fill_rectangle(x - ancho, y + dy, 2 * ancho, 1, col)


def _borrar_burbuja(display, x, y):
    r = 9
    display.fill_rectangle(x - r, y - r, 2 * r + 1, 2 * r + 1,
                            drv_display.NEGRO)
    # Restaurar la cruz central si paso por encima
    cx, cy = _W // 2, _H // 2
    # Linea horizontal de la cruz
    x0 = max(cx - 40, x - r)
    x1 = min(cx + 40, x + r)
    if x1 > x0 and (y - r) <= cy <= (y + r):
        display.fill_rectangle(x0, cy, x1 - x0, 1, drv_display.GRIS)
    # Linea vertical de la cruz
    y0 = max(cy - 30, y - r)
    y1 = min(cy + 30, y + r)
    if y1 > y0 and (x - r) <= cx <= (x + r):
        display.fill_rectangle(cx, y0, 1, y1 - y0, drv_display.GRIS)


# ── Calculo de inclinacion ────────────────────────────────────

def _angulos(ax, ay, az):
    """
    Pitch y roll a partir del vector gravedad (acelerometro en reposo).
    Devuelve (pitch, roll) en grados.
      pitch: inclinacion frontal/trasera   (rotacion en eje X)
      roll : inclinacion lateral izq/der   (rotacion en eje Y)
    """
    # Evitamos division por cero usando atan2
    pitch = atan2(ay, sqrt(ax * ax + az * az)) * 180.0 / pi
    roll  = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / pi
    return pitch, roll


def _mapear_burbuja(ax, ay):
    """Convierte aceleracion lateral (en g) a coordenadas de pantalla."""
    if abs(ax) < _DEAD_G: ax = 0.0
    if abs(ay) < _DEAD_G: ay = 0.0

    sx, sy = ax, ay
    if _SWAP_XY:
        sx, sy = sy, sx
    if _INV_X: sx = -sx
    if _INV_Y: sy = -sy

    cx, cy = _W // 2, _H // 2
    px = int(cx + sx * _SENS_PX)
    py = int(cy + sy * _SENS_PX)

    # Acotar al area visible (sin invadir el HUD inferior)
    px = max(12, min(_W - 12, px))
    py = max(22, min(_H - 60, py))
    return px, py


# ── Test interactivo ──────────────────────────────────────────

def correr(display=None, duracion_ms=120_000):
    """
    Ejecuta el test interactivo durante `duracion_ms`.
    Presionar el boton del joystick recalibra el IMU.
    """
    if display is None:
        display = drv_display.init_display()

    # Init del IMU (incluye una calibracion en reposo)
    print("=" * 56)
    print("test_imu: prueba MPU6050 y orientacion")
    print("Calibrando en reposo... mantener la consola plana e inmovil.")
    drv_imu.init_imu()
    print("Calibracion inicial OK.")
    print("Offsets: x={:.4f} y={:.4f} z={:.4f}".format(
        drv_imu._offset_x, drv_imu._offset_y, drv_imu._offset_z))
    print("-" * 56)
    print("Presiona el boton del joystick para recalibrar.")
    print("ax,ay,az son lecturas CALIBRADAS en g (drv_imu.leer).")
    print("crudo_*  es la lectura directa del MPU sin filtrar.")
    print("=" * 56)

    _dibujar_marco(display)
    _hud(display, "Calibrado. Inclina la consola.",
                  "BTN joystick = recalibrar",
                  "Compara la burbuja con la fisica")

    t_inicio = ticks_ms()
    px_ant, py_ant = _W // 2, _H // 2
    _burbuja(display, px_ant, py_ant, drv_display.VERDE)

    ultimo_print = 0
    intervalo_print_ms = 250
    btn_anterior = False

    while ticks_diff(ticks_ms(), t_inicio) < duracion_ms:
        ahora = ticks_ms()

        # ── Capa 1: lectura cruda directa del chip ────────────
        try:
            a = drv_imu._imu.accel
            crudo_x, crudo_y, crudo_z = a.x, a.y, a.z
        except Exception as e:
            crudo_x = crudo_y = crudo_z = float("nan")
            print("ERR lectura cruda:", e)

        # ── Capa 2: lectura calibrada + filtrada ──────────────
        ax, ay, az = drv_imu.leer()

        # ── Capa 3: angulos pitch/roll ────────────────────────
        pitch, roll = _angulos(ax, ay, az + 1.0)
        # Sumamos 1g a az porque leer() le resta 1g (era el offset en reposo)

        # ── Capa 4: posicion de la burbuja ────────────────────
        px, py = _mapear_burbuja(ax, ay)

        # Color segun cercania al centro (verde = nivelado, rojo = inclinado)
        mag = (ax * ax + ay * ay) ** 0.5
        if mag < 0.05:
            col = drv_display.VERDE
        elif mag < 0.20:
            col = drv_display.AMARILLO
        else:
            col = drv_display.ROJO

        if (px, py) != (px_ant, py_ant):
            _borrar_burbuja(display, px_ant, py_ant)
            _burbuja(display, px, py, col)
            px_ant, py_ant = px, py
        else:
            # Actualizar color sin moverse
            _burbuja(display, px, py, col)

        # ── HUD textual ───────────────────────────────────────
        if ticks_diff(ahora, ultimo_print) >= intervalo_print_ms:
            ultimo_print = ahora
            l1 = "crudo x={:+.2f} y={:+.2f} z={:+.2f}".format(
                crudo_x, crudo_y, crudo_z)
            l2 = "cal   x={:+.2f} y={:+.2f} z={:+.2f}".format(ax, ay, az)
            l3 = "pitch={:+5.1f}  roll={:+5.1f}".format(pitch, roll)
            _hud(display, l1, l2, l3)
            print(l1, "|", l2, "|", l3)

        # ── Recalibracion por boton ───────────────────────────
        btn = joy1.boton()
        if btn and not btn_anterior:
            _hud(display, "Recalibrando... no mover.", "", "")
            print("-> Recalibrando (mantener plano y quieto)")
            try:
                drv_buzzer.sfx_menu()
            except Exception:
                pass
            drv_imu.calibrar()
            print("Nuevos offsets: x={:.4f} y={:.4f} z={:.4f}".format(
                drv_imu._offset_x, drv_imu._offset_y, drv_imu._offset_z))
            try:
                drv_buzzer.sfx_seleccionar()
            except Exception:
                pass
            # Refrescar marco completo (la burbuja vuelve al centro)
            _dibujar_marco(display)
            px_ant, py_ant = _W // 2, _H // 2
            _burbuja(display, px_ant, py_ant, drv_display.VERDE)
        btn_anterior = btn

        sleep_ms(20)

    print("-" * 56)
    print("Fin test_imu.")


# Auto-ejecutar al importar
if __name__ != "__main__":
    try:
        correr()
    except KeyboardInterrupt:
        print("Interrumpido.")
