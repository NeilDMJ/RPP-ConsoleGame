"""
Juego 2: Gyro Maze
Autor: [Asignar]
Estado: PENDIENTE DE IMPLEMENTACION

Mecanica:
  - Laberinto en vista superior. Una esfera se mueve inclinando el dispositivo.
  - Objetivo: llegar a la meta evitando agujeros.
  - Modo editor: tocar la cuadricula para colocar paredes. Guardar en flash.

Hardware:
  - MPU6050 (control principal de la esfera)
  - Pantalla tactil ILI9341 (visualizacion + editor de niveles)
  - Buzzer (retroalimentacion sonora)
  - Joysticks (navegacion de menu)
"""
from drivers import display as drv_display
from drivers import touch   as drv_touch
from drivers import buzzer  as drv_buzzer
from drivers import imu     as drv_imu
from drivers import storage as drv_storage
from utime import sleep_ms, sleep_us, ticks_us, ticks_diff


JUEGO_ID = "gyro_maze"

# Tamano de celda del laberinto en pixeles
CELDA = 16
COLS  = 240 // CELDA   # 15 columnas
FILAS = 300 // CELDA   # 18 filas (dejando 20px para HUD)


def jugar(display):
    """
    Punto de entrada del juego.
    Returns:
        int: puntaje (tiempo restante convertido a puntos, o niveles completados).
    """
    # TODO: implementar logica del juego
    # Estructura sugerida:
    #
    # nivel = _cargar_nivel(0)  o nivel = _nivel_default()
    # while True:
    #   _dibujar_laberinto(display, nivel)
    #   completado = _loop_juego(display, nivel)
    #   if completado: puntaje += 100; cargar siguiente nivel
    #   else: break
    # drv_storage.guardar_record(JUEGO_ID, puntaje)
    # return puntaje

    _pantalla_pendiente(display)
    sleep_ms(2000)
    return 0


def _pantalla_pendiente(display):
    from drivers.display import NEGRO, BLANCO, CYAN
    display.fill_rectangle(0, 0, 240, 320, NEGRO)
    display.draw_text8x8(40,  140, "GYRO MAZE",  CYAN)
    display.draw_text8x8(20,  160, "EN DESARROLLO", BLANCO)


# ─── Funciones a implementar ──────────────────────────────────

def _nivel_default():
    """Devuelve la matriz del laberinto por defecto (lista de listas 0/1)."""
    # 0 = pasillo, 1 = pared, 2 = agujero, 3 = meta
    # TODO: disenar el laberinto inicial
    return [[0] * COLS for _ in range(FILAS)]


def _dibujar_laberinto(display, nivel):
    """Renderiza el laberinto completo en pantalla."""
    # TODO
    pass


def _loop_juego(display, nivel):
    """
    Loop principal del juego.
    Returns True si el jugador llego a la meta, False si cayo en un agujero.
    """
    # TODO
    return False


def _editor_niveles(display):
    """
    Modo editor: permite disenar y guardar un laberinto tocando la pantalla.
    """
    # TODO
    pass
