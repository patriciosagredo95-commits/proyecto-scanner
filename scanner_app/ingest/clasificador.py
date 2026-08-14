"""Clasificación automática de productos a partir del contenido de un RUN.

Reemplaza al viejo flujo de "nombre nuevo -> formulario manual" -- toda la
clasificación (Escuadria, Tipo, Asignación, Destino Recuperación) se deriva
directamente del Nombre de cada producto y de su Volumen Nominal [%] relativo
dentro del mismo RUN. Reglas verificadas contra
RUN_2830--...--EJEMPLO.xlsx (hoja RUN_2830 = input, hoja EJEMPLO = output)."""

from collections import Counter

import pandas as pd

from scanner_app.config import (
    ASIGNACION_CO_PRODUCTO_PRINCIPAL,
    ASIGNACION_CO_PRODUCTO_SECUNDARIO,
    ASIGNACION_PRODUCTO_PRINCIPAL,
    ASIGNACION_RECUPERACION,
    ESCUADRIA_EN_NOMBRE_REGEX,
    PREFIJO_RECUPERACION,
    TIPO_POR_PREFIJO,
)


def _prefijo(nombre: str) -> str:
    return nombre.split("_", 1)[0]


def tipo_desde_nombre(nombre: str) -> str:
    prefijo = _prefijo(nombre)
    if prefijo.isdigit():
        return "CTK"
    return TIPO_POR_PREFIJO.get(prefijo.upper(), prefijo.upper())


def es_recuperacion(nombre: str) -> bool:
    return _prefijo(nombre).upper() == PREFIJO_RECUPERACION


def parse_escuadria_desde_nombre(nombre: str) -> tuple[str, float, float] | None:
    """Ej. 'BL_20_5x143_Base' -> ('20,5x143', 20.5, 143.0)."""
    match = ESCUADRIA_EN_NOMBRE_REGEX.search(nombre)
    if not match:
        return None
    espesor = float(match.group(1).replace("_", "."))
    ancho = float(match.group(2))
    escuadria = f"{match.group(1).replace('_', ',')}x{match.group(2)}"
    return escuadria, espesor, ancho


def escuadria_dominante(nombres: list[str]) -> tuple[str, float, float] | None:
    """Moda de (espesor, ancho) entre los nombres que matchean el patrón de
    escuadria -- se asigna el mismo valor a TODAS las filas del run (confirmado
    contra el ejemplo: un producto RR sin ancho propio en su nombre queda con
    la escuadria dominante del run, no la suya)."""
    parseados = [parse_escuadria_desde_nombre(n) for n in nombres]
    parseados = [p for p in parseados if p is not None]
    if not parseados:
        return None
    conteo = Counter((esc, esp, anc) for esc, esp, anc in parseados)
    return conteo.most_common(1)[0][0]


def destino_recuperacion_desde_nombre(nombre: str) -> str | None:
    """Solo aplica a nombres RR. Quita el prefijo 'RR_' y el token de escuadria
    que sigue (patrón NNxNNN o un número simple), y limpia el resto.
    'RR_56_Base_Americana' -> 'Base Americana'; 'RR_20_5x115_Base' -> 'Base'."""
    if not es_recuperacion(nombre):
        return None
    resto = nombre.split("_", 1)[1] if "_" in nombre else ""

    match_escuadria = ESCUADRIA_EN_NOMBRE_REGEX.match(resto)
    if match_escuadria:
        resto = resto[match_escuadria.end():]
    else:
        partes = resto.split("_", 1)
        resto = partes[1] if len(partes) > 1 and partes[0].isdigit() else resto

    resto = resto.lstrip("_")
    resto = resto.replace("_", " ").strip()
    return resto or None


def _asignaciones_por_ranking(volumenes_pct: pd.Series) -> pd.Series:
    """volumenes_pct: Volumen Nominal [%] de las filas NO-recuperación de un
    mismo run. Ranking descendente: las 2 mayores -> PRODUCTO PRINCIPAL, la
    3ra -> CO-PRODUCTO PRINCIPAL, el resto -> CO-PRODUCTO SECUNDARIO."""
    orden = volumenes_pct.sort_values(ascending=False, kind="stable")
    etiquetas = pd.Series(ASIGNACION_CO_PRODUCTO_SECUNDARIO, index=orden.index)
    etiquetas.iloc[:2] = ASIGNACION_PRODUCTO_PRINCIPAL
    if len(etiquetas) >= 3:
        etiquetas.iloc[2] = ASIGNACION_CO_PRODUCTO_PRINCIPAL
    return etiquetas.reindex(volumenes_pct.index)


def clasificar_run(productos_incluidos: pd.DataFrame, escuadria_archivo_fallback: str | None = None) -> pd.DataFrame:
    """Agrega columnas de clasificación (escuadria, espesor_mm, ancho_mm, tipo,
    asignacion, destino_recuperacion) a las filas incluidas de un run.
    `productos_incluidos` debe tener al menos la columna 'nombre' y
    'volumen_nominal_pct'."""
    df = productos_incluidos.copy()

    dominante = escuadria_dominante(df["nombre"].tolist())
    if dominante is not None:
        escuadria, espesor_mm, ancho_mm = dominante
    elif escuadria_archivo_fallback:
        escuadria, espesor_mm, ancho_mm = escuadria_archivo_fallback, None, None
    else:
        escuadria, espesor_mm, ancho_mm = None, None, None
    df["escuadria"] = escuadria
    df["espesor_mm"] = espesor_mm
    df["ancho_mm"] = ancho_mm

    df["tipo"] = df["nombre"].map(tipo_desde_nombre)
    es_recup = df["nombre"].map(es_recuperacion)

    df["asignacion"] = ASIGNACION_RECUPERACION
    if (~es_recup).any():
        df.loc[~es_recup, "asignacion"] = _asignaciones_por_ranking(df.loc[~es_recup, "volumen_nominal_pct"])

    df["destino_recuperacion"] = df["nombre"].map(destino_recuperacion_desde_nombre)

    return df
