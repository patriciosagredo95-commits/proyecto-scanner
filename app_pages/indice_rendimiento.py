import streamlit as st

from scanner_app.dashboard import charts
from scanner_app.dashboard.filtros import selector_rango_fechas
from scanner_app.dashboard.rendimiento import promedio_por_lote, serie_periodo_rendimiento
from scanner_app.db import get_conn
from scanner_app.repository import facts_repo, master_repo

st.title("Índice de Rendimiento")
st.caption(
    "Rendimiento Real = rendimiento nominal (promedio por RUN) del período y la escuadria filtrados. "
    "Rendimiento Meta = rendimiento nominal promedio histórico de la escuadria seleccionada, "
    "considerando todos los datos disponibles en la base de datos (no depende del filtro de fechas)."
)

conn = get_conn()


@st.cache_data(ttl="2m")
def _cargar_escuadrias() -> list[str]:
    with get_conn().session as s:
        return master_repo.get_escuadrias_distintas(s)


@st.cache_data(ttl="2m")
def cargar_datos(fecha_desde, fecha_hasta, escuadria, incluir_rechazo):
    with get_conn().session as s:
        return facts_repo.load_production(
            s, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, escuadria=escuadria, incluir_rechazo=incluir_rechazo
        )


with st.sidebar:
    st.header("Filtros")
    fecha_desde, fecha_hasta = selector_rango_fechas(
        "ir",
        {"Últimos 30 días": 30, "Últimos 90 días": 90, "Últimos 120 días": 120},
        default="Últimos 90 días",
    )
    escuadria_sel = st.selectbox("Escuadria", ["Todas", *_cargar_escuadrias()], key="ir_escuadria")
    incluir_rechazo = st.checkbox("Incluir corridas de Rechazo", value=False, key="ir_rechazo")
    agrupacion = st.segmented_control("Agrupar por", ["Día", "Semana", "Mes"], default="Día", key="ir_agrupacion") or "Día"
    if st.button("Actualizar ahora", icon=":material/refresh:", key="ir_actualizar"):
        st.cache_data.clear()
        st.rerun()

escuadria_param = None if escuadria_sel == "Todas" else escuadria_sel

df_periodo = cargar_datos(fecha_desde, fecha_hasta, escuadria_param, incluir_rechazo)
df_historico = cargar_datos(None, None, escuadria_param, incluir_rechazo)

if df_periodo.empty:
    st.info("No hay datos de producción para los filtros seleccionados.")
    st.stop()

rendimiento_meta = promedio_por_lote(df_historico)
serie_real = serie_periodo_rendimiento(df_periodo, agrupacion)

st.caption(f"Periodo: {fecha_desde:%d-%m-%Y} a {fecha_hasta:%d-%m-%Y}  |  Escuadria: {escuadria_sel}")

col1, col2 = st.columns(2)
col1.metric("Rendimiento Real", f"{promedio_por_lote(df_periodo):,.1f}%", help="Promedio por RUN, acotado al período y escuadria filtrados.")
col2.metric(
    "Rendimiento Meta", f"{rendimiento_meta:,.1f}%",
    help="Promedio por RUN de la escuadria seleccionada, con todos los datos históricos disponibles.",
)

with st.container(border=True):
    st.subheader("Rendimiento Real vs Meta en el tiempo")
    st.altair_chart(charts.rendimiento_real_vs_meta(serie_real, rendimiento_meta, agrupacion), width="stretch")
