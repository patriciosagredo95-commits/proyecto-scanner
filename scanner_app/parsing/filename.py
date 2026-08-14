"""Extracción best-effort de señales del nombre de archivo RUN.

RUN/Fecha/Turno ya NO se leen del nombre de archivo -- vienen de la metadata
interna del archivo (tabla izquierda, ver parsing/run_file.py), que es estable
sin importar qué convención de nombre se haya usado al exportar. Esto es
necesario porque, de los 688 archivos RUN reales, 152 usan una convención de
nombre distinta a "RUN_XXXX--YYYY-MM-DD--...(--)" (ej.
"RUN_2073--16_04_26_TURNO_DÍA_48_75_..._ok.xlsx").

Lo que queda acá es puramente informativo / para warnings blandos: nunca
bloquea la carga de un archivo.
"""

from dataclasses import dataclass

from scanner_app.config import ESCUADRIA_EN_ARCHIVO_REGEX


@dataclass(frozen=True)
class NombreArchivoRun:
    nombre_archivo: str
    escuadria_archivo: str | None
    es_rechazo: bool


def parse_filename(nombre_archivo: str) -> NombreArchivoRun:
    """Nunca lanza excepción -- cualquier nombre de archivo .xlsx es aceptado."""
    es_rechazo = "rechazo" in nombre_archivo.lower()

    match = ESCUADRIA_EN_ARCHIVO_REGEX.search(nombre_archivo)
    escuadria_archivo = None
    if match:
        espesor_texto = match.group(1).replace("_", ",").replace(".", ",")
        escuadria_archivo = f"{espesor_texto}x{match.group(2)}"

    return NombreArchivoRun(
        nombre_archivo=nombre_archivo,
        escuadria_archivo=escuadria_archivo,
        es_rechazo=es_rechazo,
    )


def normalizar_escuadria(token: str) -> str:
    """Normaliza un token de escuadria (ej. '20.5X143') al formato usado
    internamente ('20,5x143'), para comparaciones blandas. No garantiza un
    match exacto -- es solo para advertencias, no para validación dura."""
    return token.replace(".", ",").lower()
