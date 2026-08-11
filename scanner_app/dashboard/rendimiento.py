"""Cálculo del 'Rendimiento' al estilo del reporte de referencia
('Reporte Scanner a la fecha.xlsx', hoja 'Dashboard Escuadria'/'Analisis Mes').

Fórmulas reconstruidas a partir de las fórmulas reales del Excel (GETPIVOTDATA
y AVERAGE sobre pivots) y verificadas contra los datos reales:

- Rendimiento Total/Turno = promedio, entre todos los lotes (Fecha, Turno,
  Escuadria), de la SUMA de REND VOL N % de ese lote. Los lotes sin filas de
  la categoría cuentan como 0 (no se excluyen del promedio) -- así reproduce
  el comportamiento de un pivot con AVERAGE sobre una columna de SUMIFS.
- Rendimiento a Blank/CTK = % del Volumen Nominal total atribuible a ese Tipo
  (fracción simple, no promedio por lote).
- % Bajo Espesor = % del Volumen Nominal total con Obs Espesor='Bajo Espesor'.
- Rendimiento por Asignación = igual método que Total/Turno, pero filtrando a
  esa Asignación antes de sumar por lote.

Validado contra el histórico real: Total, Turno 1/2 y Blank coinciden con el
Excel de referencia dentro de ~1 punto porcentual. El desglose por Asignación
específica quedó con una diferencia de algunos puntos que no se pudo cerrar
del todo (el Excel de referencia parece ser una foto de los datos en otro
momento, ligeramente distinta al histórico actual) -- se documenta como
limitación conocida, no se debe asumir precisión decimal exacta ahí.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class RendimientoMensual:
    total: float
    turno_1: float
    turno_2: float
    blank: float
    ctk: float
    pct_bajo_espesor: float
    producto_principal: float
    co_producto_principal: float
    co_producto_secundario: float
    recuperacion: float


def _promedio_por_lote(
    df: pd.DataFrame,
    agrupar_por: tuple[str, ...] = ("fecha", "turno", "escuadria"),
    filtro_col: str | None = None,
    filtro_val: str | None = None,
) -> float:
    if df.empty:
        return 0.0
    agrupar_por = [c for c in agrupar_por if c in df.columns]
    todos_lotes = list(df.groupby(agrupar_por).groups.keys())
    datos = df if filtro_col is None else df[df[filtro_col] == filtro_val]
    suma_por_lote = datos.groupby(agrupar_por)["rend_vol_n_pct"].sum()
    suma_por_lote = suma_por_lote.reindex(todos_lotes, fill_value=0)
    return float(suma_por_lote.mean() * 100) if len(suma_por_lote) else 0.0


def calcular_rendimiento_mensual(df: pd.DataFrame) -> RendimientoMensual:
    if df.empty:
        return RendimientoMensual(*([0.0] * 10))

    vol_total = float(df["volumen_nominal_m3"].sum())

    def pct_del_volumen(columna: str, valor: str) -> float:
        if vol_total <= 0:
            return 0.0
        return float(df.loc[df[columna] == valor, "volumen_nominal_m3"].sum() / vol_total * 100)

    return RendimientoMensual(
        total=_promedio_por_lote(df),
        turno_1=_promedio_por_lote(df[df["turno"] == 1], agrupar_por=("fecha", "escuadria")),
        turno_2=_promedio_por_lote(df[df["turno"] == 2], agrupar_por=("fecha", "escuadria")),
        blank=pct_del_volumen("tipo", "BLANK"),
        ctk=pct_del_volumen("tipo", "CTK"),
        pct_bajo_espesor=pct_del_volumen("obs_espesor", "Bajo Espesor"),
        producto_principal=_promedio_por_lote(df, filtro_col="asignacion", filtro_val="Producto Principal"),
        co_producto_principal=_promedio_por_lote(df, filtro_col="asignacion", filtro_val="Co-Producto Principal"),
        co_producto_secundario=_promedio_por_lote(df, filtro_col="asignacion", filtro_val="Co-Producto Secundario"),
        recuperacion=_promedio_por_lote(df, filtro_col="asignacion", filtro_val="Recuperación"),
    )


def serie_diaria_rendimiento(df: pd.DataFrame) -> pd.DataFrame:
    """Formato largo (fecha, serie, valor) para graficar Total/Turno 1/Turno 2
    día a día -- cada punto promedia los lotes (turno, escuadria) [o solo
    escuadria, para las series de turno] presentes ESE día."""
    if df.empty:
        return pd.DataFrame(columns=["fecha", "serie", "valor"])

    filas = []
    for fecha, grupo in df.groupby("fecha"):
        filas.append({"fecha": fecha, "serie": "Total", "valor": _promedio_por_lote(grupo, agrupar_por=("turno", "escuadria"))})
        for turno, etiqueta in ((1, "Turno 1"), (2, "Turno 2")):
            sub = grupo[grupo["turno"] == turno]
            if not sub.empty:
                filas.append({"fecha": fecha, "serie": etiqueta, "valor": _promedio_por_lote(sub, agrupar_por=("escuadria",))})
    return pd.DataFrame(filas)
