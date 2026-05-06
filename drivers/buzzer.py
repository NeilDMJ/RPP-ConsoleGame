"""
Driver del buzzer pasivo.
Genera tonos via PWM con frecuencia y duracion configurables.
Pin: GP22 segun la propuesta.
"""
from machine import PWM, Pin
from utime import sleep_ms

_pwm  = None
_PIN  = 22


def init_buzzer():
    """Inicializa el PWM del buzzer."""
    global _pwm
    _pwm = PWM(Pin(_PIN))
    _pwm.duty_u16(0)


def tono(freq, ms, duty=30000):
    """
    Emite un tono de frecuencia y duracion indicadas.
    Args:
        freq (int): Frecuencia en Hz.
        ms   (int): Duracion en milisegundos.
        duty (int): Ciclo de trabajo 0-65535 (default ~46%, sonido suave).
    """
    _pwm.freq(freq)
    _pwm.duty_u16(duty)
    sleep_ms(ms)
    _pwm.duty_u16(0)


def silencio():
    """Apaga el buzzer inmediatamente."""
    _pwm.duty_u16(0)


# ── Efectos de sonido del proyecto ────────────────────────────

def sfx_menu():
    """Navegacion de menu."""
    tono(523, 40)   # Do5

def sfx_seleccionar():
    """Confirmar seleccion."""
    tono(659, 50)
    tono(784, 80)

def sfx_punto():
    """Punto anotado / evento positivo."""
    tono(880, 50)
    tono(1046, 80)

def sfx_error():
    """Secuencia incorrecta / fallo."""
    tono(300, 120)
    tono(200, 180)

def sfx_game_over():
    """Fin de partida."""
    for f in [440, 370, 311, 261]:
        tono(f, 140)

def sfx_nivel_up():
    """Subir de nivel."""
    for f in [523, 659, 784, 1046]:
        tono(f, 70)

def sfx_disparo():
    """Disparo (Tank Wars / Asteroids)."""
    tono(800, 30)
    tono(400, 30)

def sfx_explosion():
    """Explosion."""
    for f in [200, 150, 100]:
        tono(f, 60)

def sfx_simon(color_idx):
    """
    Tono asociado a cada cuadrante de Simon Says.
    color_idx: 0=rojo, 1=verde, 2=azul, 3=amarillo
    """
    frecuencias = [415, 310, 252, 209]
    tono(frecuencias[color_idx % 4], 300)
