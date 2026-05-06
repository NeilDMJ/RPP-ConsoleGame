"""
Modulo de almacenamiento persistente en flash (RF-08).
Guarda y recupera records de cada juego en formato JSON.
Ruta: /records.json en el sistema de archivos de la Pico W.
"""
import json
import os

_RUTA = "/records.json"

# Estructura por defecto — un record por juego
_DEFAULT = {
    "simon_says":  {"record": 0, "nombre": "---"},
    "gyro_maze":   {"record": 0, "nombre": "---"},
    "tank_wars":   {"record": 0, "nombre": "---"},
    "asteroids":   {"record": 0, "nombre": "---"},
}


def _cargar_todo():
    """Lee el archivo JSON. Si no existe o esta corrupto, devuelve defaults."""
    try:
        with open(_RUTA, "r") as f:
            datos = json.load(f)
        # Asegurar que existan todas las claves
        for k, v in _DEFAULT.items():
            if k not in datos:
                datos[k] = v
        return datos
    except Exception:
        return dict(_DEFAULT)


def _guardar_todo(datos):
    """Escribe el archivo JSON en flash."""
    with open(_RUTA, "w") as f:
        json.dump(datos, f)


def obtener_record(juego):
    """
    Devuelve el record del juego indicado.
    Args:
        juego (str): Clave del juego ('simon_says', 'gyro_maze', etc.)
    Returns:
        dict con {'record': int, 'nombre': str}
    """
    datos = _cargar_todo()
    return datos.get(juego, _DEFAULT.get(juego, {"record": 0, "nombre": "---"}))


def guardar_record(juego, puntaje, nombre="AAA"):
    """
    Guarda el record si el puntaje supera al anterior.
    Args:
        juego   (str): Clave del juego.
        puntaje (int): Nuevo puntaje.
        nombre  (str): Iniciales del jugador (max 3 chars).
    Returns:
        bool: True si se rompio el record anterior.
    """
    datos   = _cargar_todo()
    actual  = datos.get(juego, {"record": 0, "nombre": "---"})
    if puntaje > actual["record"]:
        datos[juego] = {"record": puntaje, "nombre": nombre[:3].upper()}
        _guardar_todo(datos)
        return True
    return False


def reset_records():
    """Borra todos los records (para pruebas)."""
    _guardar_todo(dict(_DEFAULT))
