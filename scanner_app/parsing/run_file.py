"""Parseo del contenido de un archivo RUN_XXXX.xlsx: metadata (lado izquierdo)
y tabla de productos (lado derecho, "Productos")."""

from dataclasses import dataclass
from datetime import datetime

import openpyxl
import pandas as pd

from scanner_app.config import (
    RUN_META_COL_ETIQUETA,
    RUN_META_COL_VALOR,
    RUN_META_FILAS,
    RUN_PRODUCTOS_ANCHO_MAX,
    RUN_PRODUCTOS_COL_INICIO,
    RUN_PRODUCTOS_FILA_HEADER,
    RUN_PRODUCTOS_FILA_INICIO_DATOS,
    RUN_PRODUCTOS_HEADERS_REQUERIDOS,
    RUN_TOTAL_CORTES_ETIQUETA,
    RUN_TOTAL_CORTES_FILA,
    RUN_TOTAL_COL_VALOR,
)


@dataclass(frozen=True)
class MetadataRun:
    run_numero_interno: int
    estado: str | None
    operador: str | None
    turno_texto: str | None
    comienzo: datetime | None
    fin: datetime | None
    total_cortes: int


@dataclass(frozen=True)
class ArchivoRunParseado:
    hoja: str
    metadata: MetadataRun
    productos: pd.DataFrame  # todas las filas leídas (incluidas y excluidas)


def _normalizar_header(valor) -> str:
    """Colapsa saltos de línea y espacios repetidos a un solo espacio: el archivo
    trae los encabezados con un salto de línea antes de la unidad y un espacio al
    final, y así quedan comparables con RUN_PRODUCTOS_HEADERS_REQUERIDOS."""
    if valor is None:
        return ""
    return " ".join(str(valor).split())


def _leer_valor_meta(ws, campo: str) -> str | None:
    fila_esperada, etiqueta_esperada = RUN_META_FILAS[campo]
    etiqueta_en_fila = ws.cell(row=fila_esperada, column=RUN_META_COL_ETIQUETA).value
    if etiqueta_en_fila is not None and str(etiqueta_en_fila).strip() == etiqueta_esperada:
        return ws.cell(row=fila_esperada, column=RUN_META_COL_VALOR).value

    # Fallback: la posición fija no coincidió (layout pudo haberse corrido);
    # escanear toda la columna A buscando la etiqueta exacta.
    for fila in range(1, ws.max_row + 1):
        valor = ws.cell(row=fila, column=RUN_META_COL_ETIQUETA).value
        if valor is not None and str(valor).strip() == etiqueta_esperada:
            return ws.cell(row=fila, column=RUN_META_COL_VALOR).value

    raise ValueError(
        f"No se encontró la etiqueta '{etiqueta_esperada}' esperada para el campo "
        f"'{campo}' en el archivo (ni en la fila {fila_esperada} ni en el resto de la columna A)."
    )


def _leer_total_cortes(ws) -> int:
    """Total de Cortes del RUN completo (bloque 'Total', fila 29 columna A =
    'Cortes' / columna C = valor -- ver RUN_TOTAL_COL_VALOR). No es una columna
    de la tabla 'Productos': el archivo no trae el desglose por producto."""
    etiqueta_en_fila = ws.cell(row=RUN_TOTAL_CORTES_FILA, column=RUN_META_COL_ETIQUETA).value
    if etiqueta_en_fila is not None and str(etiqueta_en_fila).strip() == RUN_TOTAL_CORTES_ETIQUETA:
        valor = ws.cell(row=RUN_TOTAL_CORTES_FILA, column=RUN_TOTAL_COL_VALOR).value
        if valor is not None:
            return int(valor)

    # Fallback: igual que _leer_valor_meta, escanear toda la columna A.
    for fila in range(1, ws.max_row + 1):
        etiqueta = ws.cell(row=fila, column=RUN_META_COL_ETIQUETA).value
        if etiqueta is not None and str(etiqueta).strip() == RUN_TOTAL_CORTES_ETIQUETA:
            valor = ws.cell(row=fila, column=RUN_TOTAL_COL_VALOR).value
            if valor is not None:
                return int(valor)

    raise ValueError(
        f"No se encontró la etiqueta '{RUN_TOTAL_CORTES_ETIQUETA}' esperada para el Total de Cortes "
        f"(ni en la fila {RUN_TOTAL_CORTES_FILA} ni en el resto de la columna A)."
    )


def _parse_datetime(valor) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    return datetime.strptime(str(valor).strip(), "%d-%m-%Y %H:%M")


def _leer_metadata(ws) -> MetadataRun:
    run_numero_texto = _leer_valor_meta(ws, "run_numero")
    if run_numero_texto is None:
        raise ValueError("No se pudo leer el número de RUN interno del archivo.")
    digitos = "".join(ch for ch in str(run_numero_texto) if ch.isdigit())
    if not digitos:
        raise ValueError(f"El valor de RUN interno '{run_numero_texto}' no contiene dígitos.")
    run_numero_interno = int(digitos)

    return MetadataRun(
        run_numero_interno=run_numero_interno,
        estado=_leer_valor_meta(ws, "estado"),
        operador=_leer_valor_meta(ws, "operador"),
        turno_texto=_leer_valor_meta(ws, "turno"),
        comienzo=_parse_datetime(_leer_valor_meta(ws, "comienzo")),
        fin=_parse_datetime(_leer_valor_meta(ws, "fin")),
        total_cortes=_leer_total_cortes(ws),
    )


def _leer_columnas_productos(ws) -> dict[str, int]:
    """Mapea nombre de encabezado normalizado -> número de columna.

    Ni el orden ni el conjunto de columnas son estables entre archivos: el
    scanner exporta las columnas que tenga configuradas. A partir del 26-08-2026
    los archivos traen 19 columnas (se agregó "Cantidad [ % ]") en vez de las 18
    previas, y reordenadas. Por eso la fila de encabezados se lee completa (hasta
    la primera celda vacía) y solo se exige que estén las columnas que se leen.
    """
    columna_por_header: dict[str, int] = {}
    for i in range(RUN_PRODUCTOS_ANCHO_MAX):
        columna = RUN_PRODUCTOS_COL_INICIO + i
        header = _normalizar_header(ws.cell(row=RUN_PRODUCTOS_FILA_HEADER, column=columna).value)
        if header == "":
            break
        columna_por_header.setdefault(header, columna)

    faltantes = [h for h in RUN_PRODUCTOS_HEADERS_REQUERIDOS if h not in columna_por_header]
    if faltantes:
        raise ValueError(
            "La tabla 'Productos' no tiene todas las columnas necesarias. "
            f"Faltan: {faltantes!r}. Encontradas: {list(columna_por_header)!r}. "
            "Es probable que el scanner haya exportado el archivo con otra "
            "configuración de columnas."
        )
    return columna_por_header


def _leer_productos(ws) -> pd.DataFrame:
    col_index = _leer_columnas_productos(ws)
    col_nombre = col_index["Nombre"]
    col_estado = col_index["Estado"]
    col_calidad = col_index["Calidad"]
    col_volumen_nominal_m3 = col_index["Volumen Nominal [ m³ ]"]
    col_cantidad_pcs = col_index["Cantidad [ pcs ]"]
    col_largo_pct = col_index["Largo [ % ]"]
    col_largo_m = col_index["Largo [ m ]"]
    col_largo_maximo = col_index["Largo Máximo"]
    col_largo_minimo = col_index["Largo Mínimo"]
    col_largo_promedio_m = col_index["Largo Promedio [ m ]"]
    col_volumen_nominal_pct = col_index["Volumen Nominal [ % ]"]
    col_volumen_m3 = col_index["Volumen [ m³ ]"]  # solo para el agregado a nivel de run, no se persiste por producto

    filas = []
    fila = RUN_PRODUCTOS_FILA_INICIO_DATOS
    while True:
        nombre = ws.cell(row=fila, column=col_nombre).value
        if nombre is None or str(nombre).strip() == "":
            break
        cantidad_pcs = ws.cell(row=fila, column=col_cantidad_pcs).value or 0
        volumen_nominal_m3 = ws.cell(row=fila, column=col_volumen_nominal_m3).value
        estado = ws.cell(row=fila, column=col_estado).value
        # Regla de inclusión: solo Cantidad y Volumen Nominal > 0 -- el campo
        # Estado NO se usa para filtrar (confirmado contra RUN_2830--EJEMPLO,
        # que incluye una fila "Inactivo" con cantidad y volumen > 0).
        incluido = cantidad_pcs > 0 and (volumen_nominal_m3 or 0) > 0
        filas.append(
            {
                "nombre": str(nombre).strip(),
                "estado": estado,
                "calidad": ws.cell(row=fila, column=col_calidad).value,
                "volumen_nominal_m3": volumen_nominal_m3,
                "cantidad_pcs": cantidad_pcs,
                "largo_pct": ws.cell(row=fila, column=col_largo_pct).value,
                "largo_m": ws.cell(row=fila, column=col_largo_m).value,
                "largo_maximo": ws.cell(row=fila, column=col_largo_maximo).value,
                "largo_minimo": ws.cell(row=fila, column=col_largo_minimo).value,
                "largo_promedio_m": ws.cell(row=fila, column=col_largo_promedio_m).value,
                "volumen_nominal_pct": ws.cell(row=fila, column=col_volumen_nominal_pct).value,
                "volumen_m3": ws.cell(row=fila, column=col_volumen_m3).value,
                "incluido": incluido,
            }
        )
        fila += 1

    return pd.DataFrame(filas)


def parse_run_file(archivo) -> ArchivoRunParseado:
    """archivo: ruta o file-like (ej. UploadedFile de Streamlit)."""
    wb = openpyxl.load_workbook(archivo, data_only=True)
    hoja = wb.sheetnames[0]
    ws = wb[hoja]
    metadata = _leer_metadata(ws)
    productos = _leer_productos(ws)
    return ArchivoRunParseado(hoja=hoja, metadata=metadata, productos=productos)
