"""Cálculo de los KPIs del dashboard a partir del DataFrame consolidado que
devuelve facts_repo.load_production (columnas de v_production)."""

from dataclasses import dataclass

import pandas as pd

from scanner_app.dashboard.rendimiento import promedio_por_lote


@dataclass
class Kpis:
    volumen_nominal_m3: float
    rendimiento_pct: float  # promedio por lote (fecha+turno+escuadria) de REND VOL N % -- ver rendimiento.promedio_por_lote
    cantidad_pcs: int
    num_runs: int
    pct_rechazo: float  # sobre piezas, incluye producción + rechazo


def calcular_kpis(df: pd.DataFrame) -> Kpis:
    if df.empty:
        return Kpis(0.0, 0.0, 0, 0, 0.0)

    volumen_nominal_m3 = float(df["volumen_nominal_m3"].sum())
    cantidad_pcs = int(df["cantidad_pcs"].sum())
    num_runs = int(df["run_id"].dropna().nunique())

    rendimiento_pct = promedio_por_lote(df)

    if cantidad_pcs > 0:
        pct_rechazo = float(df.loc[df["es_rechazo"], "cantidad_pcs"].sum() / cantidad_pcs * 100)
    else:
        pct_rechazo = 0.0

    return Kpis(volumen_nominal_m3, rendimiento_pct, cantidad_pcs, num_runs, pct_rechazo)


def delta_pct(actual: float, anterior: float) -> float | None:
    """Delta porcentual para st.metric. None si no hay base de comparación."""
    if anterior in (0, None):
        return None
    return (actual - anterior) / anterior * 100
