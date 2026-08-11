"""Reglas de negocio duras (bloquean la carga) y blandas (advertencias) sobre
un archivo RUN ya parseado. Los errores duros de *estructura* (nombre de
archivo, headers de la tabla Productos) ya se lanzan como ValueError durante
el parseo -- ver scanner_app/parsing/. Este módulo cubre las reglas que
requieren cruzar el archivo con el estado de la base de datos."""

from dataclasses import dataclass, field

from scanner_app.config import TURNO_NUMERO_A_TEXTO, TURNO_TEXTO_A_NUMERO
from scanner_app.parsing.filename import NombreArchivoRun, normalizar_escuadria
from scanner_app.parsing.run_file import ArchivoRunParseado
from scanner_app.repository import runs_repo


@dataclass
class ResultadoValidacion:
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        return not self.errores


def validar_run(
    conn,
    nombre_parseado: NombreArchivoRun,
    archivo_parseado: ArchivoRunParseado,
    permitir_duplicado: bool = False,
) -> ResultadoValidacion:
    resultado = ResultadoValidacion()

    if archivo_parseado.metadata.run_numero_interno != nombre_parseado.run_numero:
        resultado.errores.append(
            f"El número de RUN interno del archivo (RUN_{archivo_parseado.metadata.run_numero_interno}) "
            f"no coincide con el del nombre de archivo (RUN_{nombre_parseado.run_numero}). "
            "Es probable que el archivo haya sido renombrado manualmente."
        )

    if not permitir_duplicado and runs_repo.exists_run_numero(conn, nombre_parseado.run_numero):
        resultado.errores.append(
            f"Ya existe una carga previa para RUN_{nombre_parseado.run_numero}. "
            "Use la opción 'forzar recarga' si desea reemplazar los datos existentes."
        )

    turno_interno = None
    if archivo_parseado.metadata.turno_texto:
        turno_interno = TURNO_TEXTO_A_NUMERO.get(archivo_parseado.metadata.turno_texto.strip().lower())
    if (
        nombre_parseado.turno_archivo is not None
        and turno_interno is not None
        and nombre_parseado.turno_archivo != turno_interno
    ):
        resultado.advertencias.append(
            f"El turno del nombre de archivo ({TURNO_NUMERO_A_TEXTO[nombre_parseado.turno_archivo]}) "
            f"difiere del turno interno del archivo ({archivo_parseado.metadata.turno_texto}). "
            "Se usará el turno del nombre de archivo."
        )
    elif nombre_parseado.turno_archivo is None:
        resultado.advertencias.append(
            "No se pudo determinar el turno a partir del nombre de archivo; "
            "se usará el turno indicado dentro del archivo."
        )

    if archivo_parseado.productos.empty:
        resultado.errores.append("El archivo no contiene ninguna fila en la tabla de productos.")
    elif not archivo_parseado.productos["incluido"].any():
        resultado.errores.append(
            "Todas las filas de productos están inactivas o con cantidad 0; no hay nada que cargar."
        )

    return resultado


def advertencias_escuadria(
    nombre_parseado: NombreArchivoRun,
    productos_incluidos_por_nombre: list[str],
    master_por_nombre: dict[str, dict],
) -> list[str]:
    """Comparación blanda entre la escuadria del nombre de archivo y la
    escuadria registrada en la tabla maestra para cada nombre involucrado."""
    if not nombre_parseado.escuadria_archivo:
        return []

    esc_archivo_norm = normalizar_escuadria(nombre_parseado.escuadria_archivo)
    advertencias = []
    for nombre in productos_incluidos_por_nombre:
        registro = master_por_nombre.get(nombre)
        if registro and registro.get("escuadria"):
            esc_master_norm = str(registro["escuadria"]).strip().lower()
            if esc_archivo_norm != esc_master_norm:
                advertencias.append(
                    f"'{nombre}': la escuadria del archivo ({nombre_parseado.escuadria_archivo}) "
                    f"difiere de la escuadria registrada en la tabla maestra ({registro['escuadria']})."
                )
    return advertencias
