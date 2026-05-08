"""
Driver para encoder rotativo KY-040.
Pines fisicos 12, 14, 15 (GP9, GP10, GP11).
CLK -> GP9, DT -> GP10, SW -> GP11, GND -> pin 13, + -> 3V3.
Usa interrupcion en CLK para no perder pulsos.
"""
from machine import Pin


class Encoder:
    def __init__(self, pin_clk, pin_dt, pin_sw=None):
        self._clk = Pin(pin_clk, Pin.IN, Pin.PULL_UP)
        self._dt  = Pin(pin_dt,  Pin.IN, Pin.PULL_UP)
        self._sw  = Pin(pin_sw,  Pin.IN, Pin.PULL_UP) if pin_sw is not None else None
        self._last_clk = self._clk.value()
        self._counter  = 0
        self._clk.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
                      handler=self._on_clk)

    def _on_clk(self, pin):
        clk = self._clk.value()
        if clk == self._last_clk:
            return
        dt = self._dt.value()
        if dt != clk:
            self._counter += 1
        else:
            self._counter -= 1
        self._last_clk = clk

    def delta(self):
        """Devuelve cambio acumulado desde la ultima llamada y resetea."""
        d = self._counter
        self._counter = 0
        return d // 2  # cada detent = 2 transiciones

    def boton(self):
        if self._sw is None:
            return False
        return self._sw.value() == 0


encoder1 = Encoder(pin_clk=9, pin_dt=10, pin_sw=11)
