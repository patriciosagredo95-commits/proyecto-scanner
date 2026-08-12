"""Gráficos Altair del dashboard. Paleta categórica de orden fijo (nunca
ciclada) tomada del set validado de la skill dataviz -- mismos 8 hex en el
mismo orden en cada render, así una categoría siempre tiene el mismo color."""

import altair as alt
import pandas as pd

_PALETTE = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
}
_ORDEN_CATEGORICO = ["blue", "orange", "aqua", "yellow", "magenta", "green", "violet", "red"]

# Vega expression functions (day/date/month/year) leen la fecha en hora local,
# igual que el formato por defecto que reemplazan -- Vega-Lite no trae nombres
# de día/mes en español y Streamlit no reenvía la opción timeFormatLocale de
# vega-embed, así que se arman los labels a mano con estos arreglos.
_DIAS_ES = "['dom','lun','mar','mié','jue','vie','sáb']"
_MESES_ES = "['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']"
_LABEL_EXPR_DIA = f"{_DIAS_ES}[day(datum.value)] + ' ' + date(datum.value)"
_LABEL_EXPR_SEMANA = f"date(datum.value) + ' ' + {_MESES_ES}[month(datum.value)]"
_LABEL_EXPR_MES = f"{_MESES_ES}[month(datum.value)] + ' ' + year(datum.value)"


def _axis_fecha(agrupacion: str = "Día") -> alt.Axis:
    label_expr = {"Semana": _LABEL_EXPR_SEMANA, "Mes": _LABEL_EXPR_MES}.get(agrupacion, _LABEL_EXPR_DIA)
    return alt.Axis(title="Fecha", labelExpr=label_expr)


def _escala_categorica(dominio: list[str]) -> alt.Scale:
    colores = [_PALETTE[_ORDEN_CATEGORICO[i % len(_ORDEN_CATEGORICO)]] for i in range(len(dominio))]
    return alt.Scale(domain=dominio, range=colores)


def _agrupar_periodo(df: pd.DataFrame, agrupacion: str) -> pd.Series:
    fechas = pd.to_datetime(df["fecha"])
    if agrupacion == "Semana":
        return fechas.dt.to_period("W").dt.start_time
    if agrupacion == "Mes":
        return fechas.dt.to_period("M").dt.start_time
    return fechas


def volumen_en_el_tiempo(df: pd.DataFrame, agrupacion: str = "Día", incluir_rechazo: bool = True) -> alt.Chart:
    datos = df.copy()
    datos["periodo"] = _agrupar_periodo(datos, agrupacion)

    if incluir_rechazo:
        datos["categoria"] = datos["es_rechazo"].map({True: "Rechazo", False: "Producción"})
        agregado = datos.groupby(["periodo", "categoria"], as_index=False)["volumen_nominal_m3"].sum()
        color = alt.Color(
            "categoria:N", title="", scale=_escala_categorica(["Producción", "Rechazo"])
        )
        tooltip_extra = [alt.Tooltip("categoria:N", title="Categoría")]
    else:
        agregado = datos.groupby("periodo", as_index=False)["volumen_nominal_m3"].sum()
        color = alt.value(_PALETTE["blue"])
        tooltip_extra = []

    return (
        alt.Chart(agregado)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("periodo:T", axis=_axis_fecha(agrupacion)),
            y=alt.Y("volumen_nominal_m3:Q", title="Volumen Nominal [m³]"),
            color=color,
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"), *tooltip_extra,
                     alt.Tooltip("volumen_nominal_m3:Q", title="Volumen Nominal [m³]", format=".2f")],
        )
        .properties(height=300)
    )


def rendimiento_en_el_tiempo(serie_diaria: pd.DataFrame) -> alt.Chart:
    """serie_diaria: salida de rendimiento.serie_diaria_rendimiento -- se
    grafica solo la serie 'Total' (rendimiento nominal promedio entre los
    RUN/lotes de cada día), no un promedio ponderado por fila."""
    datos = serie_diaria[serie_diaria["serie"] == "Total"]

    return (
        alt.Chart(datos)
        .mark_line(point=True, strokeWidth=2, color=_PALETTE["blue"])
        .encode(
            x=alt.X("fecha:T", axis=_axis_fecha("Día")),
            y=alt.Y("valor:Q", title="Rendimiento Total Nominal [%]"),
            tooltip=[alt.Tooltip("fecha:T", title="Fecha"),
                     alt.Tooltip("valor:Q", title="Rendimiento [%]", format=".1f")],
        )
        .properties(height=300)
    )


def distribucion_por_dimension(df: pd.DataFrame, dimension: str, metrica: str = "volumen_nominal_m3") -> alt.Chart:
    agregado = (
        df.groupby(dimension, as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
    )
    dominio = agregado[dimension].astype(str).tolist()

    return (
        alt.Chart(agregado)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(f"{metrica}:Q", title=metrica),
            y=alt.Y(f"{dimension}:N", sort="-x", title=dimension),
            color=alt.Color(f"{dimension}:N", legend=None, scale=_escala_categorica(dominio)),
            tooltip=[alt.Tooltip(f"{dimension}:N"), alt.Tooltip(f"{metrica}:Q", format=".2f")],
        )
        .properties(height=max(200, 32 * len(agregado)))
    )


def rendimiento_diario(serie_larga: pd.DataFrame) -> alt.Chart:
    """serie_larga: columnas fecha, serie ('Total'/'Turno 1'/'Turno 2'), valor
    [%]. Total en rojo (como en el reporte de referencia), turnos en azul/naranja."""
    dominio = ["Total", "Turno 1", "Turno 2"]
    escala = alt.Scale(domain=dominio, range=[_PALETTE["red"], _PALETTE["blue"], _PALETTE["orange"]])

    return (
        alt.Chart(serie_larga)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("valor:Q", title="Rendimiento [%]"),
            color=alt.Color("serie:N", title="", scale=escala),
            tooltip=[alt.Tooltip("fecha:T", title="Fecha"), alt.Tooltip("serie:N", title="Serie"),
                     alt.Tooltip("valor:Q", title="Rendimiento [%]", format=".1f")],
        )
        .properties(height=350)
    )


def top_escuadrias(df: pd.DataFrame, n: int = 10, metrica: str = "volumen_nominal_m3") -> alt.Chart:
    agregado = (
        df.groupby("escuadria", as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
        .head(n)
    )

    return (
        alt.Chart(agregado)
        .mark_bar(color=_PALETTE["blue"], cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(f"{metrica}:Q", title=metrica),
            y=alt.Y("escuadria:N", sort="-x", title="Escuadria"),
            tooltip=[alt.Tooltip("escuadria:N", title="Escuadria"), alt.Tooltip(f"{metrica}:Q", format=".2f")],
        )
        .properties(height=max(200, 28 * len(agregado)))
    )
