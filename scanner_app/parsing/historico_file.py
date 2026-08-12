"""Parseo de 'Base de datos Scanner.xlsx' (histórico ya acumulado) y derivación
de la tabla maestra inicial (último valor por Nombre según fecha) más las filas
de hechos de producción correspondientes."""

import pandas as pd

from scanner_app.config import HISTORICO_HEADERS, HISTORICO_HOJA

# Orden posicional 1:1 con HISTORICO_HEADERS.
_COLUMNAS_NORMALIZADAS = [
    "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm", "turno", "fecha",
    "destino_origen", "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor", "nombre",
    "volumen_nominal_m3", "largo_pct", "cantidad_pcs", "largo_m", "largo_promedio_m",
    "volumen_nominal_pct", "_rend_ln_pct_original", "_rend_vol_n_pct_original",
]

_COLUMNAS_MAESTRA = [
    "nombre", "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm",
    "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor",
]

_COLUMNAS_FACTS = [
    "nombre", "fecha", "turno", "volumen_nominal_m3", "largo_pct", "cantidad_pcs",
    "largo_m", "largo_promedio_m", "volumen_nominal_pct",
    # Clasificación cruda de ESA fila (foto histórica, no la vigente de la
    # tabla maestra) -- así el desglose por Tipo/Asignación/Escuadria coincide
    # con los reportes/pivots armados directo sobre el Excel original.
    "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm",
    "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor",
]


def load_historico(ruta) -> pd.DataFrame:
    """Lee 'Base de datos Scanner.xlsx' y devuelve un DataFrame con columnas
    normalizadas (snake_case). Lanza ValueError si los encabezados no coinciden
    con lo esperado (protección ante cambios de formato del archivo fuente)."""
    df = pd.read_excel(ruta, sheet_name=HISTORICO_HOJA, header=0)
    columnas_encontradas = list(df.columns)
    if columnas_encontradas != HISTORICO_HEADERS:
        raise ValueError(
            "Los encabezados de 'Base de datos Scanner.xlsx' no coinciden con lo esperado.\n"
            f"Encontrado: {columnas_encontradas!r}\nEsperado: {HISTORICO_HEADERS!r}"
        )

    df.columns = _COLUMNAS_NORMALIZADAS
    df = df.dropna(subset=["nombre"]).copy()
    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df["turno"] = df["turno"].astype(int)
    df["cantidad_pcs"] = df["cantidad_pcs"].astype(int)
    return df


def _destino_recuperacion_dominante(df_historico: pd.DataFrame) -> pd.Series:
    """Valor más frecuente de destino_recuperacion por nombre (moda), indexado
    por nombre. A diferencia del resto de las columnas de clasificación, este
    campo trae errores de tipeo puntuales en el histórico (ej. una sola fila
    con "Mueble" entre 48 filas con "Estructura" para el mismo nombre) que la
    regla "último valor gana" adoptaría como vigente. Empates en cantidad se
    resuelven con la fecha más reciente entre los empatados."""
    df_no_nulo = df_historico.dropna(subset=["destino_recuperacion"])
    conteos = (
        df_no_nulo.groupby(["nombre", "destino_recuperacion"])["fecha"]
        .agg(cantidad="size", ultima_fecha="max")
        .reset_index()
        .sort_values(["cantidad", "ultima_fecha"], ascending=[False, False])
    )
    return conteos.groupby("nombre").head(1).set_index("nombre")["destino_recuperacion"]


def build_master_desde_historico(df_historico: pd.DataFrame) -> pd.DataFrame:
    """Tabla maestra inicial: último valor (por fecha) de cada Nombre.
    Regla de negocio confirmada: ante clasificaciones que cambiaron en el
    histórico para un mismo Nombre, se usa la más reciente como vigente.
    Excepción: destino_recuperacion usa la moda en vez del último valor (ver
    _destino_recuperacion_dominante) porque sus variaciones en el histórico
    son mayormente errores de tipeo puntuales, no reclasificaciones reales."""
    df_ordenado = df_historico.sort_values(["nombre", "fecha"])
    ultimo_por_nombre = df_ordenado.groupby("nombre", as_index=False).tail(1)

    maestra = ultimo_por_nombre[_COLUMNAS_MAESTRA].copy()
    dominante = _destino_recuperacion_dominante(df_historico)
    maestra["destino_recuperacion"] = maestra["nombre"].map(dominante)
    maestra["fecha_referencia"] = ultimo_por_nombre["fecha"].values
    maestra["origen"] = "historico"
    maestra["pendiente_revision"] = False
    return maestra.reset_index(drop=True)


def build_facts_desde_historico(df_historico: pd.DataFrame) -> pd.DataFrame:
    """Filas de production_facts derivadas del histórico. rend_ln_pct y
    rend_vol_n_pct siempre se recalculan, no se confía en las columnas
    REND LN %/REND VOL N % del archivo origen aunque coincidan."""
    facts = df_historico[_COLUMNAS_FACTS].copy()
    facts["fuente"] = "historico"
    facts["run_id"] = None
    facts["es_rechazo"] = False
    facts["rend_ln_pct"] = facts["largo_pct"] / 100
    facts["rend_vol_n_pct"] = facts["volumen_nominal_pct"] / 100
    return facts.reset_index(drop=True)
