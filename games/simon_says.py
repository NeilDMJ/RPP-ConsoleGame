"""
Juego 1: Simon Says Plus
Autor: [Asignar]
Estado: PENDIENTE DE IMPLEMENTACION

Mecanica:
  - Pantalla dividida en 4 cuadrantes de colores (rojo, verde, azul, amarillo).
  - El sistema reproduce una secuencia que el jugador repite tocando los cuadrantes.
  - A partir del nivel 5 se intercalan gestos de inclinacion con el MPU6050.
  - Cada ronda correcta suma puntos y agrega un elemento a la secuencia.

Hardware:
  - Pantalla tactil ILI9341 (entrada + salida)
  - Buzzer (tono por color)
  - MPU6050 (gestos a partir del nivel 5)
  - Joysticks (navegacion de menu)
"""
from drivers import display as drv_display
from drivers import touch   as drv_touch
from drivers import buzzer  as drv_buzzer
from drivers import imu     as drv_imu
from drivers import storage as drv_storage
from utime import sleep_ms


JUEGO_ID = "simon_says"


def jugar(display):
    """
    Punto de entrada del juego. Llamado desde main.py.
    Args:
        display: objeto Display ya inicializado.
    Returns:
        int: puntaje final de la partida.
    """
    # TODO: implementar logica del juego
    # Estructura sugerida:
    #
    # 1. _dibujar_cuadrantes(display)
    # 2. secuencia = []
    # 3. while True:
    #      a. Agregar color aleatorio a secuencia
    #      b. _reproducir_secuencia(display, secuencia)
    #      c. correcto = _esperar_input(display, secuencia)
    #      d. if not correcto: break
    #      e. puntaje += len(secuencia) * 10
    # 4. drv_storage.guardar_record(JUEGO_ID, puntaje)
    # 5. return puntaje

    _pantalla_pendiente(display)
    sleep_ms(2000)
    return 0


def _pantalla_pendiente(display):
    """Placeholder visual hasta implementar el juego."""
    from drivers.display import NEGRO, BLANCO, AMARILLO
    display.fill_rectangle(0, 0, 240, 320, NEGRO)
    display.draw_text8x8(30,  140, "SIMON SAYS",  AMARILLO)
    display.draw_text8x8(20,  160, "EN DESARROLLO", BLANCO)


# ─── Funciones a implementar ──────────────────────────────────

def _dibujar_cuadrantes(display):
    """Dibuja los 4 cuadrantes de colores en pantalla."""
    # TODO
    pass


def _iluminar(display, idx, encendido):
    """Ilumina o apaga el cuadrante idx (0-3)."""
    # TODO
    pass


def _reproducir_secuencia(display, secuencia):
    """Muestra y suena la secuencia actual."""
    # TODO
    pass


def _esperar_input(display, secuencia):
    """
    Espera que el jugador repita la secuencia.
    Devuelve True si fue correcta, False si fallo.
    """
    # TODO
    return False
