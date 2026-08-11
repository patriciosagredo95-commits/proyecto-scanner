"""Parseo del nombre de archivo RUN.

Formato: RUN_XXXX--YYYY-MM-DD--ESCUADRIA-DESCRIPCION[-TURNO-DIA|-TURNO-NOCHE][-RECHAZO].xlsx

Verificado contra los 4 archivos de ejemplo reales, incluyendo el caso donde
coexisten los sufijos -TURNO-DIA y -RECHAZO (el orden de estrictura importa:
-RECHAZO se quita primero porque va más a la derecha).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime

from scanner_app.config import FILENAME_REGEX, TURNO_DIA, TURNO_NOCHE

_ESCUADRIA_REGEX = re.compile(r"^(?P<escuadria>[\d.,]+[xX][\d.,]+)-(?P<descripcion>.+)$")
_SUFIJO_RECHAZO = re.compile(r"-RECHAZO$", re.IGNORECASE)
_SUFIJO_TURNO = re.compile(r"-TURNO-(DIA|D[ÍI]A|NOCHE)$", re.IGNORECASE)


@dataclass(frozen=True)
class NombreArchivoRun:
    run_numero: int
    fecha: date
    escuadria_archivo: str | None
    descripcion_archivo: str
    turno_archivo: int | None
    es_rechazo: bool
    nombre_archivo: str


def parse_filename(nombre_archivo: str) -> NombreArchivoRun:
    """Extrae run_numero, fecha, escuadria, descripción, turno y flag de rechazo
    del nombre de archivo. Lanza ValueError si el nombre no matchea el patrón
    esperado (regla dura de validación)."""
    match = re.match(FILENAME_REGEX, nombre_archivo)
    if not match:
        raise ValueError(
            f"El nombre de archivo '{nombre_archivo}' no matchea el patrón esperado "
            "'RUN_XXXX--YYYY-MM-DD--ESCUADRIA-DESCRIPCION.xlsx'."
        )

    run_numero = int(match.group("run_numero"))
    fecha = datetime.strptime(match.group("fecha"), "%Y-%m-%d").date()
    resto = match.group("resto")

    es_rechazo = bool(_SUFIJO_RECHAZO.search(resto))
    if es_rechazo:
        resto = _SUFIJO_RECHAZO.sub("", resto)

    turno_archivo = None
    turno_match = _SUFIJO_TURNO.search(resto)
    if turno_match:
        texto_turno = turno_match.group(1).lower()
        turno_archivo = TURNO_NOCHE if texto_turno == "noche" else TURNO_DIA
        resto = _SUFIJO_TURNO.sub("", resto)

    escuadria_match = _ESCUADRIA_REGEX.match(resto)
    if escuadria_match:
        escuadria_archivo = escuadria_match.group("escuadria")
        descripcion_archivo = escuadria_match.group("descripcion")
    else:
        escuadria_archivo = None
        descripcion_archivo = resto

    return NombreArchivoRun(
        run_numero=run_numero,
        fecha=fecha,
        escuadria_archivo=escuadria_archivo,
        descripcion_archivo=descripcion_archivo,
        turno_archivo=turno_archivo,
        es_rechazo=es_rechazo,
        nombre_archivo=nombre_archivo,
    )


def normalizar_escuadria(token: str) -> str:
    """Normaliza un token de escuadria del nombre de archivo (ej. '20.5X143')
    al formato usado en la tabla maestra (ej. '20,5x143'), para comparaciones
    blandas. No garantiza un match exacto -- es solo para advertencias, no para
    validación dura."""
    return token.replace(".", ",").lower()
