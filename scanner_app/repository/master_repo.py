"""Acceso a datos de master_products. Las funciones reciben una conexión/sesión
SQLAlchemy (`conn`) con método .execute(text(...), params) -- funciona tanto con
una Session de Streamlit (conn.session) como con una Connection de un Engine
plano (scripts/seed_inicial.py)."""

import pandas as pd
from sqlalchemy import text

from scanner_app.db_utils import filas_a_dataframe, registros_sql

_UPSERT_SQL = text(
    """
    INSERT INTO master_products (
        nombre, escuadria, espesor_mm, ancho_mm, calidad, tipo,
        asignacion, destino_recuperacion, fecha_referencia
    ) VALUES (
        :nombre, :escuadria, :espesor_mm, :ancho_mm, :calidad, :tipo,
        :asignacion, :destino_recuperacion, :fecha_referencia
    )
    ON CONFLICT (nombre) DO UPDATE SET
        escuadria = EXCLUDED.escuadria,
        espesor_mm = EXCLUDED.espesor_mm,
        ancho_mm = EXCLUDED.ancho_mm,
        calidad = EXCLUDED.calidad,
        tipo = EXCLUDED.tipo,
        asignacion = EXCLUDED.asignacion,
        destino_recuperacion = EXCLUDED.destino_recuperacion,
        fecha_referencia = EXCLUDED.fecha_referencia,
        actualizado_en = now()
    """
)


def get_by_nombre(conn, nombre: str) -> dict | None:
    row = conn.execute(text("SELECT * FROM master_products WHERE nombre = :nombre"), {"nombre": nombre}).mappings().first()
    return dict(row) if row else None


def existen_nombres(conn, nombres: list[str]) -> set[str]:
    """Subconjunto de `nombres` que ya existe en la tabla maestra."""
    if not nombres:
        return set()
    rows = conn.execute(
        text("SELECT nombre FROM master_products WHERE nombre = ANY(:nombres)"),
        {"nombres": list(nombres)},
    ).all()
    return {r[0] for r in rows}


def get_all(conn) -> pd.DataFrame:
    rows = conn.execute(text("SELECT * FROM master_products ORDER BY nombre")).mappings().all()
    return filas_a_dataframe(rows)


def get_escuadrias_distintas(conn) -> list[str]:
    rows = conn.execute(
        text("SELECT DISTINCT escuadria FROM master_products WHERE escuadria IS NOT NULL ORDER BY escuadria")
    ).all()
    return [r[0] for r in rows]


def upsert(conn, registro: dict) -> None:
    conn.execute(_UPSERT_SQL, registro)


def bulk_upsert(conn, df_maestra: pd.DataFrame) -> None:
    registros = registros_sql(df_maestra)
    if registros:
        conn.execute(_UPSERT_SQL, registros)
