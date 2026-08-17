"""Acceso a datos de runs (control de cargas, defensa contra duplicados)."""

import pandas as pd
from sqlalchemy import text

from scanner_app.db_utils import filas_a_dataframe

_INSERT_SQL = text(
    """
    INSERT INTO runs (
        run_numero, nombre_archivo, fecha, turno, escuadria_archivo,
        es_rechazo, operador, hora_comienzo, hora_fin,
        cantidad_total_pcs, largo_total_m, volumen_total_m3, volumen_nominal_total_m3, total_cortes,
        filas_activas, filas_excluidas, productos_nuevos
    ) VALUES (
        :run_numero, :nombre_archivo, :fecha, :turno, :escuadria_archivo,
        :es_rechazo, :operador, :hora_comienzo, :hora_fin,
        :cantidad_total_pcs, :largo_total_m, :volumen_total_m3, :volumen_nominal_total_m3, :total_cortes,
        :filas_activas, :filas_excluidas, :productos_nuevos
    )
    RETURNING id
    """
)


def exists_run_numero(conn, run_numero: int) -> bool:
    """Sin caché -- se usa en el camino de escritura para evitar duplicados."""
    row = conn.execute(text("SELECT 1 FROM runs WHERE run_numero = :n"), {"n": run_numero}).first()
    return row is not None


def insert_run(conn, registro: dict) -> int:
    return conn.execute(_INSERT_SQL, registro).scalar_one()


def delete_run_cascade(conn, run_numero: int) -> None:
    """Borra el run y (vía ON DELETE CASCADE) todos sus production_facts.
    Usado solo en el flujo explícito de 'forzar recarga'."""
    conn.execute(text("DELETE FROM runs WHERE run_numero = :n"), {"n": run_numero})


def list_runs(conn, limite: int = 100) -> pd.DataFrame:
    rows = conn.execute(
        text("SELECT * FROM runs ORDER BY creado_en DESC LIMIT :limite"), {"limite": limite}
    ).mappings().all()
    return filas_a_dataframe(rows)
