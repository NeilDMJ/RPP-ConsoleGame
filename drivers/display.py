"""
Driver de pantalla ILI9341.
Orientacion horizontal (landscape): 320x240
"""
from ili9341 import Display, color565
from machine import Pin, SPI


def init_display():
    spi = SPI(1, baudrate=40_000_000, sck=Pin(14), mosi=Pin(15))
    display = Display(spi, dc=Pin(6), cs=Pin(17), rst=Pin(7),
                      width=320, height=240, rotation=90)
    display.clear()
    return display


def color(r, g, b):
    return color565(r, g, b)


# Paleta comun
NEGRO    = color565(0,   0,   0)
BLANCO   = color565(255, 255, 255)
ROJO     = color565(220, 40,  40)
VERDE    = color565(0,   200, 60)
AZUL     = color565(30,  100, 220)
AMARILLO = color565(255, 210, 0)
CYAN     = color565(0,   220, 220)
MAGENTA  = color565(200, 0,   200)
GRIS     = color565(80,  80,  80)
GRIS_OSC = color565(30,  30,  30)
