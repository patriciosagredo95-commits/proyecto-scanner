"""Cálculo del 'Rendimiento' al estilo del reporte de referencia
('Reporte Scanner a la fecha.xlsx', hoja 'Dashboard Escuadria'/'Analisis Mes').

Fórmulas reconstruidas a partir de las fórmulas reales del Excel (GETPIVOTDATA
y AVERAGE sobre pivots):

- Rendimiento Total/Turno = promedio, entre todos los RUN, de la SUMA de
  Volumen Nominal [%] de ese RUN (las filas incluidas de un mismo RUN suman
  ~100% de su propio volumen nominal). Los RUN sin filas de la categoría
  cuentan como 0 (no se excluyen del promedio) -- así reproduce el
  comportamiento de un pivot con AVERAGE sobre una columna de SUMIFS.
  IMPORTANTE: la unidad de "lote" es el RUN (run_id), no la combinación
  (Fecha, Turno, Escuadria) -- dos RUN distintos pueden compartir esa misma
  combinación (ej. dos cargas separadas el mismo día/turno/escuadria), y
  sumar sus % antes de promediar da un "rendimiento" que supera el 100%.
- Rendimiento a Blank/CTK = % del Volumen Nominal total atribuible a ese Tipo
  (fracción simple, no promedio por RUN).
- Rendimiento por Asignación = igual método que Total/Turno, pero filtrando a
  esa Asignación antes de sumar por RUN.
"""

from dataclasses import dataclass

import pandas as pd

from scanner_app.config import (
    ASIGNACION_CO_PRODUCTO_PRINCIPAL,
    ASIGNACION_CO_PRODUCTO_SECUNDARIO,
    ASIGNACION_PRODUCTO_PRINCIPAL,
    ASIGNACION_RECUPERACION,
)


@dataclass
class RendimientoMensual:
    total: float
    turno_1: float
    turno_2: float
    turno_3: float
    blank: float
    ctk: float
    producto_principal: float
    co_producto_principal: float
    co_producto_secundario: float
    recuperacion: float


def promedio_por_lote(
    df: pd.DataFrame,
    agrupar_por: tuple[str, ...] = ("run_id",),
    filtro_col: str | None = None,
    filtro_val: str | None = None,
) -> float:
    """Promedio, entre todos los RUN presentes en `df`, de la SUMA de
    Volumen Nominal [%] de ese RUN (o de la porción filtrada por
    filtro_col/filtro_val). `agrupar_por` por defecto es ("run_id",) -- cada
    RUN es un lote; no cambiar a columnas como (fecha, turno, escuadria), que
    no identifican un RUN de forma única (ver docstring del módulo)."""
    if df.empty:
        return 0.0
    agrupar_por = [c for c in agrupar_por if c in df.columns]
    todos_lotes = list(df.groupby(agrupar_por).groups.keys())
    datos = df if filtro_col is None else df[df[filtro_col] == filtro_val]
    suma_por_lote = datos.groupby(agrupar_por)["volumen_nominal_pct"].sum()
    suma_por_lote = suma_por_lote.reindex(todos_lotes, fill_value=0)
    return float(suma_por_lote.mean() * 100) if len(suma_por_lote) else 0.0


def calcular_rendimiento_mensual(df: pd.DataFrame) -> RendimientoMensual:
    if df.empty:
        return RendimientoMensual(*([0.0] * 11))

    vol_total = float(df["volumen_nominal_m3"].sum())

    def pct_del_volumen(columna: str, valor: str) -> float:
        if vol_total <= 0:
            return 0.0
        return float(df.loc[df[columna] == valor, "volumen_nominal_m3"].sum() / vol_total * 100)

    return RendimientoMensual(
        total=promedio_por_lote(df),
        turno_1=promedio_por_lote(df[df["turno"] == 1]),
        turno_2=promedio_por_lote(df[df["turno"] == 2]),
        turno_3=promedio_por_lote(df[df["turno"] == 3]),
        blank=pct_del_volumen("tipo", "BLANK"),
        ctk=pct_del_volumen("tipo", "CTK"),
        producto_principal=promedio_por_lote(df, filtro_col="asignacion", filtro_val=ASIGNACION_PRODUCTO_PRINCIPAL),
        co_producto_principal=promedio_por_lote(df, filtro_col="asignacion", filtro_val=ASIGNACION_CO_PRODUCTO_PRINCIPAL),
        co_producto_secundario=promedio_por_lote(df, filtro_col="asignacion", filtro_val=ASIGNACION_CO_PRODUCTO_SECUNDARIO),
        recuperacion=promedio_por_lote(df, filtro_col="asignacion", filtro_val=ASIGNACION_RECUPERACION),
    )


def agrupar_periodo(df: pd.DataFrame, agrupacion: str) -> pd.Series:
    """Bucket de fecha según agrupación (Día/Semana/Mes), como el inicio del
    período correspondiente. Usado tanto para agregaciones de volumen/cortes
    (charts.py) como para serie_periodo_rendimiento (abajo)."""
    fechas = pd.to_datetime(df["fecha"])
    if agrupacion == "Semana":
        return fechas.dt.to_period("W").dt.start_time
    if agrupacion == "Mes":
        return fechas.dt.to_period("M").dt.start_time
    return fechas


def serie_periodo_rendimiento(df: pd.DataFrame, agrupacion: str = "Día") -> pd.DataFrame:
    """Rendimiento Real por período (Día/Semana/Mes): mismo método que
    promedio_por_lote (promedio, entre los RUN de ese período, de la SUMA de
    Volumen Nominal [%] de ese RUN), agregado en columnas (periodo, valor)."""
    if df.empty:
        return pd.DataFrame(columns=["periodo", "valor"])

    datos = df.copy()
    datos["periodo"] = agrupar_periodo(datos, agrupacion)
    filas = [
        {"periodo": periodo, "valor": promedio_por_lote(grupo)} for periodo, grupo in datos.groupby("periodo")
    ]
    return pd.DataFrame(filas).sort_values("periodo").reset_index(drop=True)


def serie_diaria_rendimiento(df: pd.DataFrame) -> pd.DataFrame:
    """Formato largo (fecha, serie, valor) para graficar Total/Turno 1/Turno 2/
    Turno 3 día a día -- cada punto promedia los RUN presentes ESE día
    (o, para las series de turno, los RUN de ese turno ese día)."""
    if df.empty:
        return pd.DataFrame(columns=["fecha", "serie", "valor"])

    filas = []
    for fecha, grupo in df.groupby("fecha"):
        filas.append({"fecha": fecha, "serie": "Total", "valor": promedio_por_lote(grupo)})
        for turno, etiqueta in ((1, "Turno 1"), (2, "Turno 2"), (3, "Turno 3")):
            sub = grupo[grupo["turno"] == turno]
            if not sub.empty:
                filas.append({"fecha": fecha, "serie": etiqueta, "valor": promedio_por_lote(sub)})
    return pd.DataFrame(filas)


def serie_diaria_por_asignacion(df: pd.DataFrame) -> pd.DataFrame:
    """Formato largo (fecha, asignacion, valor) -- mismo método que
    serie_diaria_rendimiento (promedio por RUN) pero desglosado por categoría
    de Asignación en vez de por turno."""
    if df.empty:
        return pd.DataFrame(columns=["fecha", "asignacion", "valor"])

    categorias = [
        ASIGNACION_PRODUCTO_PRINCIPAL,
        ASIGNACION_CO_PRODUCTO_PRINCIPAL,
        ASIGNACION_CO_PRODUCTO_SECUNDARIO,
        ASIGNACION_RECUPERACION,
    ]
    filas = []
    for fecha, grupo in df.groupby("fecha"):
        for categoria in categorias:
            sub = grupo[grupo["asignacion"] == categoria]
            if not sub.empty:
                filas.append({"fecha": fecha, "asignacion": categoria, "valor": promedio_por_lote(sub)})
    return pd.DataFrame(filas)
