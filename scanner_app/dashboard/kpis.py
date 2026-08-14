"""Cálculo de los KPIs del dashboard a partir del DataFrame consolidado que
devuelve facts_repo.load_production (columnas de v_production)."""

from dataclasses import dataclass

import pandas as pd

from scanner_app.config import TURNO_NUMERO_A_TEXTO
from scanner_app.dashboard.rendimiento import promedio_por_lote


@dataclass
class Kpis:
    volumen_nominal_m3: float
    rendimiento_pct: float  # promedio por RUN de Volumen Nominal % -- ver rendimiento.promedio_por_lote
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


def ranking_operador(df: pd.DataFrame) -> pd.DataFrame:
    """Volumen Nominal total y Rendimiento (promedio por RUN, acotado a los
    propios RUN de cada operador -- no se diluye con RUN de otros operadores)
    por Operador."""
    if df.empty or "operador" not in df.columns:
        return pd.DataFrame(columns=["operador", "volumen_nominal_m3", "rendimiento_pct"])

    datos = df.dropna(subset=["operador"])
    if datos.empty:
        return pd.DataFrame(columns=["operador", "volumen_nominal_m3", "rendimiento_pct"])

    filas = [
        {
            "operador": operador,
            "volumen_nominal_m3": float(grupo["volumen_nominal_m3"].sum()),
            "rendimiento_pct": promedio_por_lote(grupo),
        }
        for operador, grupo in datos.groupby("operador")
    ]
    return pd.DataFrame(filas).sort_values("volumen_nominal_m3", ascending=False).reset_index(drop=True)


def throughput_por_turno(df_runs: pd.DataFrame) -> pd.DataFrame:
    """m³ nominal por hora de proceso, por turno -- usa hora_comienzo/hora_fin
    y volumen_nominal_total_m3 de cada run (scanner_app.repository.runs_repo.
    load_runs_en_rango). Excluye runs sin ambas horas o con duración <= 0
    (dato corrupto/incompleto -- no debería pasar, pero no se asume)."""
    columnas = ["turno_label", "throughput_m3_h"]
    if df_runs.empty:
        return pd.DataFrame(columns=columnas)

    datos = df_runs.dropna(subset=["hora_comienzo", "hora_fin"]).copy()
    duracion_h = (pd.to_datetime(datos["hora_fin"]) - pd.to_datetime(datos["hora_comienzo"])).dt.total_seconds() / 3600
    datos = datos.loc[duracion_h > 0].copy()
    duracion_h = duracion_h.loc[duracion_h > 0]
    if datos.empty:
        return pd.DataFrame(columns=columnas)

    datos["throughput_m3_h"] = datos["volumen_nominal_total_m3"] / duracion_h
    datos["turno_label"] = datos["turno"].map(TURNO_NUMERO_A_TEXTO)
    return datos.groupby("turno_label", as_index=False)["throughput_m3_h"].mean()
