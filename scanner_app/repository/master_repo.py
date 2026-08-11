"""Acceso a datos de master_products. Las funciones reciben una conexión/sesión
SQLAlchemy (`conn`) con método .execute(text(...), params) -- funciona tanto con
una Session de Streamlit (conn.session) como con una Connection de un Engine
plano (scripts/seed_inicial.py)."""

import pandas as pd
from sqlalchemy import text

from scanner_app.config import CAMPOS_ASIGNACION_TEXTO
from scanner_app.db_utils import filas_a_dataframe, registros_sql

_UPSERT_SQL = text(
    """
    INSERT INTO master_products (
        nombre, escuadria, espesor_mm, ancho_mm, largo_nominal_mm,
        destino, tipo, asignacion, destino_recuperacion,
        pct_recuperacion, ancho_recuperacion, obs_ancho, obs_espesor,
        fecha_referencia, origen, pendiente_revision
    ) VALUES (
        :nombre, :escuadria, :espesor_mm, :ancho_mm, :largo_nominal_mm,
        :destino, :tipo, :asignacion, :destino_recuperacion,
        :pct_recuperacion, :ancho_recuperacion, :obs_ancho, :obs_espesor,
        :fecha_referencia, :origen, :pendiente_revision
    )
    ON CONFLICT (nombre) DO UPDATE SET
        escuadria = EXCLUDED.escuadria,
        espesor_mm = EXCLUDED.espesor_mm,
        ancho_mm = EXCLUDED.ancho_mm,
        largo_nominal_mm = EXCLUDED.largo_nominal_mm,
        destino = EXCLUDED.destino,
        tipo = EXCLUDED.tipo,
        asignacion = EXCLUDED.asignacion,
        destino_recuperacion = EXCLUDED.destino_recuperacion,
        pct_recuperacion = EXCLUDED.pct_recuperacion,
        ancho_recuperacion = EXCLUDED.ancho_recuperacion,
        obs_ancho = EXCLUDED.obs_ancho,
        obs_espesor = EXCLUDED.obs_espesor,
        fecha_referencia = EXCLUDED.fecha_referencia,
        origen = EXCLUDED.origen,
        pendiente_revision = EXCLUDED.pendiente_revision,
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


_COLUMNAS_CLASIFICACION = [
    "nombre", "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm",
    "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor",
]


def get_clasificacion_por_nombres(conn, nombres: list[str]) -> pd.DataFrame:
    """Clasificación VIGENTE (hoy) para un conjunto de nombres -- se usa al
    ingestar un RUN para tomar una foto de esta clasificación y grabarla en
    production_facts (ver scanner_app/ingest/loader.py)."""
    if not nombres:
        return pd.DataFrame(columns=_COLUMNAS_CLASIFICACION)
    columnas = ", ".join(_COLUMNAS_CLASIFICACION)
    rows = conn.execute(
        text(f"SELECT {columnas} FROM master_products WHERE nombre = ANY(:nombres)"),
        {"nombres": list(nombres)},
    ).mappings().all()
    return filas_a_dataframe(rows)


def get_all(conn) -> pd.DataFrame:
    rows = conn.execute(text("SELECT * FROM master_products ORDER BY nombre")).mappings().all()
    return filas_a_dataframe(rows)


def get_pendientes_revision(conn) -> pd.DataFrame:
    rows = conn.execute(
        text("SELECT * FROM master_products WHERE pendiente_revision ORDER BY nombre")
    ).mappings().all()
    return filas_a_dataframe(rows)


def get_escuadrias_distintas(conn) -> list[str]:
    rows = conn.execute(
        text("SELECT DISTINCT escuadria FROM master_products WHERE escuadria IS NOT NULL ORDER BY escuadria")
    ).all()
    return [r[0] for r in rows]


def get_valores_distintos(conn, campo: str) -> list[str]:
    if campo not in CAMPOS_ASIGNACION_TEXTO:
        raise ValueError(f"Campo no permitido para lookup de valores distintos: {campo}")
    rows = conn.execute(
        text(f"SELECT DISTINCT {campo} FROM master_products WHERE {campo} IS NOT NULL ORDER BY {campo}")
    ).all()
    return [r[0] for r in rows]


def upsert(conn, registro: dict) -> None:
    conn.execute(_UPSERT_SQL, registro)


def bulk_upsert(conn, df_maestra: pd.DataFrame) -> None:
    registros = registros_sql(df_maestra)
    if registros:
        conn.execute(_UPSERT_SQL, registros)
