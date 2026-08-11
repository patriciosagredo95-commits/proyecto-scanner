"""Utilidades compartidas para pasar DataFrames como parámetros de SQL y para
normalizar los resultados de lectura antes de usarlos en pandas/Streamlit."""

from decimal import Decimal

import pandas as pd


def registros_sql(df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame a list[dict] apto para bindear como parámetros
    de SQLAlchemy, reemplazando NaN/NaT (que pandas no distingue de None) por
    None real -- si no, psycopg2 intenta adaptar float('nan') a columnas de
    texto y falla."""
    if df.empty:
        return []
    df_obj = df.astype(object)
    return df_obj.where(df_obj.notna(), None).to_dict("records")


def filas_a_dataframe(filas) -> pd.DataFrame:
    """Construye un DataFrame a partir de filas de conn.execute(...).mappings(),
    convirtiendo las columnas NUMERIC de Postgres (que psycopg2 entrega como
    decimal.Decimal, no float) a float64 -- si no, operaciones aritméticas
    simples como sumas ponderadas fallan al mezclar Decimal con float."""
    df = pd.DataFrame(filas)
    for columna in df.columns:
        if df[columna].dtype == object and df[columna].map(lambda v: isinstance(v, Decimal)).any():
            df[columna] = df[columna].astype(float)
    return df
