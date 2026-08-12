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
            x=alt.X("periodo:T", title="Fecha"),
            y=alt.Y("volumen_nominal_m3:Q", title="Volumen Nominal [m³]"),
            color=color,
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"), *tooltip_extra,
                     alt.Tooltip("volumen_nominal_m3:Q", title="Volumen Nominal [m³]", format=".2f")],
        )
        .properties(height=300)
    )


def rendimiento_en_el_tiempo(df: pd.DataFrame, agrupacion: str = "Día") -> alt.Chart:
    datos = df.copy()
    datos["periodo"] = _agrupar_periodo(datos, agrupacion)

    def _promedio_ponderado(grupo: pd.DataFrame) -> pd.Series:
        peso = grupo["volumen_nominal_m3"].sum()
        if peso == 0:
            return pd.Series({"Rendimiento Largo %": 0.0, "Rendimiento Volumen %": 0.0})
        return pd.Series(
            {
                "Rendimiento Largo %": (grupo["rend_ln_pct"] * grupo["volumen_nominal_m3"]).sum() / peso * 100,
                "Rendimiento Volumen %": (grupo["rend_vol_n_pct"] * grupo["volumen_nominal_m3"]).sum() / peso * 100,
            }
        )

    agregado = datos.groupby("periodo").apply(_promedio_ponderado, include_groups=False).reset_index()
    largo = agregado.melt(id_vars="periodo", var_name="métrica", value_name="valor")

    return (
        alt.Chart(largo)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("periodo:T", title="Fecha"),
            y=alt.Y("valor:Q", title="Rendimiento [%]"),
            color=alt.Color(
                "métrica:N", title="",
                scale=_escala_categorica(["Rendimiento Largo %", "Rendimiento Volumen %"]),
            ),
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"), alt.Tooltip("métrica:N", title="Métrica"),
                     alt.Tooltip("valor:Q", title="Valor [%]", format=".2f")],
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
