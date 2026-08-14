"""Reglas de negocio duras (bloquean la carga) y blandas (advertencias) sobre
un archivo RUN ya parseado. Los errores duros de *estructura* (headers de la
tabla Productos) ya se lanzan como ValueError durante el parseo -- ver
scanner_app/parsing/. Este módulo cubre las reglas que requieren cruzar el
archivo con el estado de la base de datos."""

from dataclasses import dataclass, field

from scanner_app.ingest.clasificador import escuadria_dominante
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
    metadata = archivo_parseado.metadata

    if metadata.run_numero_interno is None:
        resultado.errores.append("No se pudo leer el número de RUN interno del archivo.")
    elif not permitir_duplicado and runs_repo.exists_run_numero(conn, metadata.run_numero_interno):
        resultado.errores.append(
            f"Ya existe una carga previa para RUN_{metadata.run_numero_interno}. "
            "Use la opción 'forzar recarga' si desea reemplazar los datos existentes."
        )

    if archivo_parseado.productos.empty:
        resultado.errores.append("El archivo no contiene ninguna fila en la tabla de productos.")
    elif not archivo_parseado.productos["incluido"].any():
        resultado.errores.append(
            "Todas las filas de productos tienen cantidad y/o volumen nominal 0; no hay nada que cargar."
        )

    if resultado.es_valido:
        productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]]
        resultado.advertencias.extend(
            advertencia_escuadria(nombre_parseado, productos_incluidos["nombre"].tolist())
        )

    return resultado


def advertencia_escuadria(nombre_parseado: NombreArchivoRun, nombres_incluidos: list[str]) -> list[str]:
    """Comparación blanda entre la escuadria del nombre de archivo (si se pudo
    extraer) y la escuadria dominante calculada a partir de los Nombres
    incluidos en este mismo run."""
    if not nombre_parseado.escuadria_archivo:
        return []

    dominante = escuadria_dominante(nombres_incluidos)
    if dominante is None:
        return []

    esc_archivo_norm = normalizar_escuadria(nombre_parseado.escuadria_archivo)
    esc_calculada_norm = dominante[0].strip().lower()
    if esc_archivo_norm != esc_calculada_norm:
        return [
            f"La escuadria del nombre de archivo ({nombre_parseado.escuadria_archivo}) difiere de la "
            f"escuadria calculada a partir de los productos incluidos ({dominante[0]})."
        ]
    return []
