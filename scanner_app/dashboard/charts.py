"""Gráficos Altair del dashboard. Paleta categórica de orden fijo (nunca
ciclada) tomada del set validado de la skill dataviz -- mismos 8 hex en el
mismo orden en cada render, así una categoría siempre tiene el mismo color."""

import altair as alt
import pandas as pd

from scanner_app.config import (
    ASIGNACION_CO_PRODUCTO_PRINCIPAL,
    ASIGNACION_CO_PRODUCTO_SECUNDARIO,
    ASIGNACION_PRODUCTO_PRINCIPAL,
    ASIGNACION_RECUPERACION,
)

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

# Color fijo por categoría de Asignación (no por rango/posición) -- reusa los
# primeros 4 colores del orden categórico validado, así la misma categoría
# tiene siempre el mismo color en cualquier gráfico de la app.
_COLOR_ASIGNACION = alt.Scale(
    domain=[
        ASIGNACION_PRODUCTO_PRINCIPAL,
        ASIGNACION_CO_PRODUCTO_PRINCIPAL,
        ASIGNACION_CO_PRODUCTO_SECUNDARIO,
        ASIGNACION_RECUPERACION,
    ],
    range=[_PALETTE["blue"], _PALETTE["orange"], _PALETTE["aqua"], _PALETTE["yellow"]],
)

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


_TEXT_MUTED = "#44474d"  # tinta neutra -- las etiquetas nunca llevan el color de la serie


def _capa_etiquetas(agregado: pd.DataFrame, x: str, y: str, formato: str, x_tipo: str = "T") -> alt.Chart:
    """Etiqueta de valor sobre cada punto, en tinta neutra (nunca el color de
    la serie) y desplazada arriba del punto para no toparse con la línea."""
    return (
        alt.Chart(agregado)
        .mark_text(dy=-12, fontSize=11, color=_TEXT_MUTED)
        .encode(x=f"{x}:{x_tipo}", y=f"{y}:Q", text=alt.Text(f"{y}:Q", format=formato))
    )


def volumen_en_el_tiempo(df: pd.DataFrame, agrupacion: str = "Día") -> alt.Chart:
    """Solo Producción -- las corridas de Rechazo se excluyen siempre, sin
    importar el filtro 'Incluir corridas de Rechazo' del sidebar (ese filtro
    solo controla los demás gráficos/KPIs de la página)."""
    datos = df[~df["es_rechazo"]].copy()
    datos["periodo"] = _agrupar_periodo(datos, agrupacion)
    agregado = datos.groupby("periodo", as_index=False)["volumen_nominal_m3"].sum()

    linea = (
        alt.Chart(agregado)
        .mark_line(point=True, strokeWidth=2, color=_PALETTE["blue"])
        .encode(
            x=alt.X("periodo:T", axis=_axis_fecha(agrupacion)),
            y=alt.Y("volumen_nominal_m3:Q", title="Volumen Nominal [m³]"),
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"),
                     alt.Tooltip("volumen_nominal_m3:Q", title="Volumen Nominal [m³]", format=".2f")],
        )
    )
    etiquetas = _capa_etiquetas(agregado, "periodo", "volumen_nominal_m3", ".2f")
    return alt.layer(linea, etiquetas).properties(height=300)


def metros_lineales_en_el_tiempo(df: pd.DataFrame, agrupacion: str = "Día") -> alt.Chart:
    """Solo Producción -- las corridas de Rechazo se excluyen siempre, sin
    importar el filtro 'Incluir corridas de Rechazo' del sidebar (ese filtro
    solo controla los demás gráficos/KPIs de la página)."""
    datos = df[~df["es_rechazo"]].copy()
    datos["periodo"] = _agrupar_periodo(datos, agrupacion)
    agregado = datos.groupby("periodo", as_index=False)["largo_m"].sum()

    linea = (
        alt.Chart(agregado)
        .mark_line(point=True, strokeWidth=2, color=_PALETTE["aqua"])
        .encode(
            x=alt.X("periodo:T", axis=_axis_fecha(agrupacion)),
            y=alt.Y("largo_m:Q", title="Metros Lineales [m]"),
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"),
                     alt.Tooltip("largo_m:Q", title="Metros Lineales [m]", format=",.2f")],
        )
    )
    etiquetas = _capa_etiquetas(agregado, "periodo", "largo_m", ",.0f")
    return alt.layer(linea, etiquetas).properties(height=300)


def rendimiento_en_el_tiempo(serie_diaria: pd.DataFrame) -> alt.Chart:
    """serie_diaria: salida de rendimiento.serie_diaria_rendimiento -- se
    grafica solo la serie 'Total' (rendimiento nominal promedio entre los
    RUN/lotes de cada día), no un promedio ponderado por fila."""
    datos = serie_diaria[serie_diaria["serie"] == "Total"].copy()
    datos["valor_label"] = datos["valor"].round(1).astype(str) + "%"

    linea = (
        alt.Chart(datos)
        .mark_line(point=True, strokeWidth=2, color=_PALETTE["blue"])
        .encode(
            x=alt.X("fecha:T", axis=_axis_fecha("Día")),
            y=alt.Y("valor:Q", title="Rendimiento Total Nominal [%]"),
            tooltip=[alt.Tooltip("fecha:T", title="Fecha"),
                     alt.Tooltip("valor:Q", title="Rendimiento [%]", format=".1f")],
        )
    )
    etiquetas = (
        alt.Chart(datos)
        .mark_text(dy=-12, fontSize=11, color=_TEXT_MUTED)
        .encode(x="fecha:T", y="valor:Q", text="valor_label:N")
    )
    return alt.layer(linea, etiquetas).properties(height=300)


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
    """serie_larga: columnas fecha, serie ('Total'/'Turno 1'/'Turno 2'/'Turno 3'),
    valor [%]. Total en rojo (como en el reporte de referencia), turnos en azul/naranja/aqua."""
    dominio = ["Total", "Turno 1", "Turno 2", "Turno 3"]
    escala = alt.Scale(
        domain=dominio, range=[_PALETTE["red"], _PALETTE["blue"], _PALETTE["orange"], _PALETTE["aqua"]]
    )

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


def cortes_en_el_tiempo(df: pd.DataFrame, agrupacion: str = "Día") -> alt.Chart:
    """Evolución del Total Cortes por período. total_cortes es un dato por RUN
    (no por fila de producto) -- se deduplica por run_id antes de agrupar por
    fecha para no contarlo una vez por cada producto de ese run."""
    datos = df.dropna(subset=["run_id", "total_cortes"]).drop_duplicates("run_id").copy()
    datos["periodo"] = _agrupar_periodo(datos, agrupacion)
    agregado = datos.groupby("periodo", as_index=False)["total_cortes"].sum()

    linea = (
        alt.Chart(agregado)
        .mark_line(point=True, strokeWidth=2, color=_PALETTE["violet"])
        .encode(
            x=alt.X("periodo:T", axis=_axis_fecha(agrupacion)),
            y=alt.Y("total_cortes:Q", title="Cortes"),
            tooltip=[alt.Tooltip("periodo:T", title="Fecha"),
                     alt.Tooltip("total_cortes:Q", title="Cortes", format=",.0f")],
        )
    )
    etiquetas = _capa_etiquetas(agregado, "periodo", "total_cortes", ",.0f")
    return alt.layer(linea, etiquetas).properties(height=300)


def mix_asignacion_por_escuadria(df: pd.DataFrame, n: int = 12) -> alt.Chart:
    """Barras 100% apiladas: participación de cada Asignación dentro del
    Volumen Nominal de cada Escuadria (las n escuadrias de mayor volumen)."""
    top = (
        df.groupby("escuadria", as_index=False)["volumen_nominal_m3"]
        .sum()
        .sort_values("volumen_nominal_m3", ascending=False)
        .head(n)["escuadria"]
        .tolist()
    )
    agregado = (
        df[df["escuadria"].isin(top)]
        .groupby(["escuadria", "asignacion"], as_index=False)["volumen_nominal_m3"]
        .sum()
    )

    return (
        alt.Chart(agregado)
        .mark_bar()
        .encode(
            x=alt.X("volumen_nominal_m3:Q", title="Participación del Volumen Nominal", stack="normalize", axis=alt.Axis(format="%")),
            y=alt.Y("escuadria:N", sort=top, title="Escuadria"),
            color=alt.Color("asignacion:N", title="Asignación", scale=_COLOR_ASIGNACION),
            order=alt.Order("asignacion:N"),
            tooltip=[
                alt.Tooltip("escuadria:N", title="Escuadria"),
                alt.Tooltip("asignacion:N", title="Asignación"),
                alt.Tooltip("volumen_nominal_m3:Q", title="Volumen Nominal [m³]", format=".2f"),
            ],
        )
        .properties(height=max(200, 32 * len(top)))
    )


def pareto_destino_recuperacion(df: pd.DataFrame) -> alt.Chart:
    """Volumen Nominal recuperado por Destino Recuperación, de mayor a menor."""
    agregado = (
        df.loc[df["destino_recuperacion"].notna()]
        .groupby("destino_recuperacion", as_index=False)["volumen_nominal_m3"]
        .sum()
        .sort_values("volumen_nominal_m3", ascending=False)
    )

    return (
        alt.Chart(agregado)
        .mark_bar(color=_PALETTE["yellow"], cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("volumen_nominal_m3:Q", title="Volumen Nominal [m³]"),
            y=alt.Y("destino_recuperacion:N", sort="-x", title="Destino Recuperación"),
            tooltip=[
                alt.Tooltip("destino_recuperacion:N", title="Destino Recuperación"),
                alt.Tooltip("volumen_nominal_m3:Q", title="Volumen Nominal [m³]", format=".2f"),
            ],
        )
        .properties(height=max(200, 28 * len(agregado)))
    )


def ranking_operador(df_ranking: pd.DataFrame, metrica: str = "volumen_nominal_m3") -> alt.Chart:
    """df_ranking: salida de kpis.ranking_operador."""
    titulos = {"volumen_nominal_m3": "Volumen Nominal [m³]", "rendimiento_pct": "Rendimiento [%]"}
    formatos = {"volumen_nominal_m3": ".2f", "rendimiento_pct": ".1f"}
    agregado = df_ranking.sort_values(metrica, ascending=False)

    return (
        alt.Chart(agregado)
        .mark_bar(color=_PALETTE["blue"], cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X(f"{metrica}:Q", title=titulos[metrica]),
            y=alt.Y("operador:N", sort="-x", title="Operador"),
            tooltip=[
                alt.Tooltip("operador:N", title="Operador"),
                alt.Tooltip(f"{metrica}:Q", title=titulos[metrica], format=formatos[metrica]),
            ],
        )
        .properties(height=max(200, 28 * len(agregado)))
    )


def rendimiento_por_asignacion_diario(serie: pd.DataFrame) -> alt.Chart:
    """serie: salida de rendimiento.serie_diaria_por_asignacion -- comportamiento
    en el tiempo de Producto Principal / Co-Producto Principal / Co-Producto
    Secundario / Recuperación."""
    return (
        alt.Chart(serie)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("fecha:T", axis=_axis_fecha("Día")),
            y=alt.Y("valor:Q", title="Rendimiento [%]"),
            color=alt.Color("asignacion:N", title="Asignación", scale=_COLOR_ASIGNACION),
            tooltip=[
                alt.Tooltip("fecha:T", title="Fecha"),
                alt.Tooltip("asignacion:N", title="Asignación"),
                alt.Tooltip("valor:Q", title="Rendimiento [%]", format=".1f"),
            ],
        )
        .properties(height=350)
    )
