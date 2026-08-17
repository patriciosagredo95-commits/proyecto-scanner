from datetime import date, timedelta

import streamlit as st

from scanner_app.dashboard import charts, kpis
from scanner_app.dashboard.rendimiento import serie_diaria_rendimiento
from scanner_app.db import get_conn
from scanner_app.repository import facts_repo, master_repo, runs_repo

st.title("Informe Scanner")

conn = get_conn()


@st.cache_data(ttl="2m")
def _cargar_escuadrias() -> list[str]:
    with get_conn().session as s:
        return master_repo.get_escuadrias_distintas(s)


@st.cache_data(ttl="2m")
def cargar_datos(fecha_desde, fecha_hasta, escuadria, turno, incluir_rechazo):
    with get_conn().session as s:
        return facts_repo.load_production(
            s,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            escuadria=escuadria,
            turno=turno,
            incluir_rechazo=incluir_rechazo,
        )


with st.sidebar:
    st.header("Filtros")
    hoy = date.today()
    rango_fechas = st.date_input(
        "Rango de fechas", value=(hoy - timedelta(days=30), hoy), format="YYYY-MM-DD"
    )
    escuadrias = ["Todas", *_cargar_escuadrias()]
    escuadria_sel = st.selectbox("Escuadria", escuadrias)
    turno_sel = st.selectbox("Turno", ["Ambos", "Día", "Tarde", "Noche"])
    incluir_rechazo = st.checkbox("Incluir corridas de Rechazo", value=True)
    agrupacion = st.segmented_control("Agrupar por", ["Día", "Semana", "Mes"], default="Día")
    if st.button("Actualizar ahora", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()

fecha_desde, fecha_hasta = (rango_fechas if len(rango_fechas) == 2 else (rango_fechas[0], rango_fechas[0]))
escuadria_param = None if escuadria_sel == "Todas" else escuadria_sel
turno_param = {"Día": 1, "Noche": 2, "Tarde": 3}.get(turno_sel)

df = cargar_datos(fecha_desde, fecha_hasta, escuadria_param, turno_param, incluir_rechazo)

if df.empty:
    st.info("No hay datos de producción para los filtros seleccionados.")
    st.stop()

resumen = kpis.calcular_kpis(df)

col1, col2, col3 = st.container(horizontal=True).columns(3)
col1.metric("Volumen Nominal [m³]", f"{resumen.volumen_nominal_m3:,.2f}")
col2.metric("Rendimiento Vol. Nominal [%]", f"{resumen.rendimiento_pct:,.1f}%")
col3.metric("N° de RUNs", f"{resumen.num_runs:,}")

st.divider()

col_izq, col_der = st.columns(2)
with col_izq:
    with st.container(border=True):
        st.subheader("Volumen Nominal en el tiempo")
        st.altair_chart(
            charts.volumen_en_el_tiempo(df, agrupacion=agrupacion, incluir_rechazo=incluir_rechazo),
            width="stretch",
        )
with col_der:
    with st.container(border=True):
        st.subheader("Rendimiento en el tiempo")
        serie_rendimiento = serie_diaria_rendimiento(df)
        st.altair_chart(charts.rendimiento_en_el_tiempo(serie_rendimiento), width="stretch")

col_izq2, col_der2 = st.columns(2)
with col_izq2:
    with st.container(border=True):
        st.subheader("Distribución")
        dimension = st.selectbox(
            "Agrupar por", ["asignacion", "tipo"], key="dimension_distribucion"
        )
        st.altair_chart(charts.distribucion_por_dimension(df, dimension), width="stretch")
with col_der2:
    with st.container(border=True):
        st.subheader("Top Escuadrias por Volumen Nominal")
        st.altair_chart(charts.top_escuadrias(df), width="stretch")

col_izq3, col_der3 = st.columns(2)
with col_izq3:
    with st.container(border=True):
        st.subheader("Mix de Asignación por Escuadria")
        st.altair_chart(charts.mix_asignacion_por_escuadria(df), width="stretch")
with col_der3:
    with st.container(border=True):
        st.subheader("Producción y Rendimiento por Operador")
        ranking = kpis.ranking_operador(df)
        if ranking.empty:
            st.info("No hay operador registrado para los filtros seleccionados.")
        else:
            metrica_operador = st.segmented_control(
                "Métrica", ["volumen_nominal_m3", "rendimiento_pct"],
                format_func=lambda m: "Volumen Nominal [m³]" if m == "volumen_nominal_m3" else "Rendimiento [%]",
                default="volumen_nominal_m3", key="metrica_operador",
            )
            st.altair_chart(charts.ranking_operador(ranking, metrica_operador or "volumen_nominal_m3"), width="stretch")

if "total_cortes" in df.columns:  # ausente si la base no corrió aún la migración de schema.sql
    with st.container(border=True):
        st.subheader("Cortes en el tiempo")
        st.caption("Total Cortes por RUN, agrupado según el período elegido en el sidebar.")
        st.altair_chart(charts.cortes_en_el_tiempo(df, agrupacion=agrupacion), width="stretch")

if df["destino_recuperacion"].notna().any():
    with st.container(border=True):
        st.subheader("Destino de la Recuperación")
        st.altair_chart(charts.pareto_destino_recuperacion(df), width="stretch")

st.divider()
st.subheader("RUNs recientes")
with get_conn().session as s:
    df_runs = runs_repo.list_runs(s, limite=20)
st.dataframe(df_runs, width="stretch", hide_index=True)
