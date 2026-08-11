"""Acceso a datos de production_facts, incluyendo la lectura consolidada para
el dashboard (vía la vista v_production)."""

import pandas as pd
from sqlalchemy import text

from scanner_app.db_utils import filas_a_dataframe, registros_sql

_INSERT_SQL = text(
    """
    INSERT INTO production_facts (
        run_id, fuente, nombre, fecha, turno, es_rechazo,
        escuadria, espesor_mm, ancho_mm, largo_nominal_mm,
        destino, tipo, asignacion, destino_recuperacion,
        pct_recuperacion, ancho_recuperacion, obs_ancho, obs_espesor,
        volumen_nominal_m3, largo_pct, cantidad_pcs, largo_m, largo_promedio_m,
        volumen_nominal_pct, rend_ln_pct, rend_vol_n_pct
    ) VALUES (
        :run_id, :fuente, :nombre, :fecha, :turno, :es_rechazo,
        :escuadria, :espesor_mm, :ancho_mm, :largo_nominal_mm,
        :destino, :tipo, :asignacion, :destino_recuperacion,
        :pct_recuperacion, :ancho_recuperacion, :obs_ancho, :obs_espesor,
        :volumen_nominal_m3, :largo_pct, :cantidad_pcs, :largo_m, :largo_promedio_m,
        :volumen_nominal_pct, :rend_ln_pct, :rend_vol_n_pct
    )
    """
)


def bulk_insert_facts(conn, df_facts: pd.DataFrame) -> None:
    registros = registros_sql(df_facts)
    if registros:
        conn.execute(_INSERT_SQL, registros)


def load_production(
    conn,
    fecha_desde=None,
    fecha_hasta=None,
    escuadria: str | None = None,
    turno: int | None = None,
    incluir_rechazo: bool = True,
) -> pd.DataFrame:
    """Lectura consolidada para el dashboard. Todos los valores de filtro se
    bindean como parámetros (nunca se interpolan en el SQL)."""
    condiciones = []
    params: dict = {}

    if fecha_desde is not None:
        condiciones.append("fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        condiciones.append("fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    if escuadria:
        condiciones.append("escuadria = :escuadria")
        params["escuadria"] = escuadria
    if turno is not None:
        condiciones.append("turno = :turno")
        params["turno"] = turno
    if not incluir_rechazo:
        condiciones.append("NOT es_rechazo")

    where_clause = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    sql = text(f"SELECT * FROM v_production {where_clause}")
    rows = conn.execute(sql, params).mappings().all()
    return filas_a_dataframe(rows)
