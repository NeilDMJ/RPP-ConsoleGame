"""
Driver para MPU6050 via I2C.
Proporciona lecturas calibradas y filtradas de aceleracion e inclinacion.
Requiere: https://github.com/micropython-imu/micropython-mpu9x50  -> mpu9x50.py
"""
from machine import I2C, Pin
from imu import MPU6050 as _MPU6050
from utime import sleep_ms

# ── Constantes de filtrado ────────────────────────────────────
_ALPHA      = 0.85   # filtro paso bajo (0=sin filtro, 1=sin respuesta)
_ZONA_MUERTA = 0.04  # en g — lecturas menores se tratan como 0

# ── Estado interno del filtro ─────────────────────────────────
_ax_f = 0.0
_ay_f = 0.0
_az_f = 0.0
_imu  = None
_i2c  = None


def init_imu():
    """Inicializa el bus I2C y el MPU6050. Llama una vez al arrancar."""
    global _imu, _i2c
    _i2c = I2C(0, sda=Pin(20), scl=Pin(21), freq=100_000)
    _imu = _MPU6050(_i2c)
    # Breve calentamiento
    sleep_ms(100)
    calibrar()


def calibrar(muestras=50):
    """
    Calcula el offset promedio en reposo y lo guarda como referencia.
    Dejar el dispositivo quieto y plano al llamar esta funcion.
    """
    global _offset_x, _offset_y, _offset_z
    sx, sy, sz = 0.0, 0.0, 0.0
    for _ in range(muestras):
        a = _imu.accel
        sx += a.x; sy += a.y; sz += a.z
        sleep_ms(5)
    _offset_x = sx / muestras
    _offset_y = sy / muestras
    _offset_z = (sz / muestras) - 1.0  # restar 1g del eje Z


_offset_x = 0.0
_offset_y = 0.0
_offset_z = 0.0


def _zona_muerta(val):
    if abs(val) < _ZONA_MUERTA:
        return 0.0
    s = 1 if val > 0 else -1
    return s * (abs(val) - _ZONA_MUERTA) / (1.0 - _ZONA_MUERTA)


def leer():
    """
    Lee el acelerometro, aplica calibracion y filtro paso bajo.
    Devuelve (ax, ay, az) en g, con zona muerta aplicada.
    Maneja errores I2C internamente — si falla devuelve el ultimo valor.
    """
    global _ax_f, _ay_f, _az_f, _imu, _i2c
    try:
        a = _imu.accel
        raw_x = a.x - _offset_x
        raw_y = a.y - _offset_y
        raw_z = a.z - _offset_z
    except Exception:
        # Reintentar reinicializando I2C
        sleep_ms(30)
        try:
            init_imu()
        except Exception:
            pass
        return _zona_muerta(_ax_f), _zona_muerta(_ay_f), _zona_muerta(_az_f)

    _ax_f = _ALPHA * _ax_f + (1.0 - _ALPHA) * raw_x
    _ay_f = _ALPHA * _ay_f + (1.0 - _ALPHA) * raw_y
    _az_f = _ALPHA * _az_f + (1.0 - _ALPHA) * raw_z

    return _zona_muerta(_ax_f), _zona_muerta(_ay_f), _zona_muerta(_az_f)


def sacudida(umbral=1.8):
    """
    Devuelve True si se detecta una sacudida brusca.
    Util para el hiperespacio de Asteroids.
    umbral: magnitud en g que considera sacudida (default 1.8g).
    """
    ax, ay, az = leer()
    magnitud = (ax*ax + ay*ay + az*az) ** 0.5
    return magnitud > umbral
