"""
Driver para dos joysticks analogicos KY-023.
Lee los ejes X/Y via ADC y el boton via GPIO.
Devuelve valores normalizados de -1.0 a 1.0 con zona muerta aplicada.
"""
from machine import ADC, Pin

# ── Zona muerta ───────────────────────────────────────────────
# Lecturas dentro de este rango alrededor del centro se tratan como 0.
# Ajustar si los joysticks derivan en reposo.
_ZONA_MUERTA = 0.08

# Centro ADC (16 bits): idealmente 32768 — puede calibrarse
_CENTRO = 32768
_RANGO  = 32768  # distancia maxima desde el centro


def _normalizar(raw):
    """Convierte lectura ADC de 16 bits a float -1.0 a 1.0 con zona muerta."""
    val = (raw - _CENTRO) / _RANGO
    val = max(-1.0, min(1.0, val))
    if abs(val) < _ZONA_MUERTA:
        return 0.0
    # Escalar para que la zona muerta no cree un salto brusco
    signo = 1 if val > 0 else -1
    return signo * (abs(val) - _ZONA_MUERTA) / (1.0 - _ZONA_MUERTA)


class Joystick:
    """Un joystick KY-023 con dos ejes ADC y un boton digital."""

    def __init__(self, pin_x, pin_y, pin_btn, invertir_x=False, invertir_y=False):
        self._adc_x = ADC(Pin(pin_x))
        self._adc_y = ADC(Pin(pin_y))
        self._btn   = Pin(pin_btn, Pin.IN, Pin.PULL_UP)  # era PULL_DOWN
        self._inv_x = -1 if invertir_x else 1
        self._inv_y = -1 if invertir_y else 1

    def x(self):
        """Eje X normalizado: -1.0 (izquierda) a 1.0 (derecha)."""
        return _normalizar(self._adc_x.read_u16()) * self._inv_x

    def y(self):
        """Eje Y normalizado: -1.0 (arriba) a 1.0 (abajo)."""
        return _normalizar(self._adc_y.read_u16()) * self._inv_y

    def xy(self):
        """Devuelve (x, y) como tupla."""
        return self.x(), self.y()

    def boton(self):
        return self._btn.value() == 0  # era == 1, invertir para PULL_UP

    def direccion(self, umbral=0.4):
        """
        Devuelve la direccion discreta dominante o None.
        Retorna: 'arr', 'abj', 'izq', 'der', o None.
        """
        x, y = self.xy()
        if abs(x) > abs(y):
            if x >  umbral: return "der"
            if x < -umbral: return "izq"
        else:
            if y < -umbral: return "arr"
            if y >  umbral: return "abj"
        return None

joy1 = Joystick(pin_x=26, pin_y=27, pin_btn=2)
joy2 = Joystick(pin_x=28, pin_y=29, pin_btn=3)
