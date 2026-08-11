from datetime import date, timedelta

import streamlit as st

from scanner_app.dashboard import charts
from scanner_app.dashboard.rendimiento import calcular_rendimiento_mensual, serie_diaria_rendimiento
from scanner_app.db import get_conn
from scanner_app.repository import facts_repo, master_repo

st.title("Rendimiento Mensual Scanner")
st.caption(
    "Rendimiento = % del volumen nominal aprovechado sobre el total procesado por lote "
    "(Fecha + Turno + Escuadria), replicando la metodología del reporte histórico en Excel."
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
    hoy = date.today()
    rango_fechas = st.date_input(
        "Rango de fechas", value=(hoy - timedelta(days=120), hoy), format="YYYY-MM-DD", key="rm_fechas"
    )
    escuadria_sel = st.selectbox("Escuadria", ["Todas", *_cargar_escuadrias()], key="rm_escuadria")
    incluir_rechazo = st.checkbox("Incluir corridas de Rechazo", value=False, key="rm_rechazo")
    if st.button("Actualizar ahora", icon=":material/refresh:", key="rm_actualizar"):
        st.cache_data.clear()
        st.rerun()

fecha_desde, fecha_hasta = (rango_fechas if len(rango_fechas) == 2 else (rango_fechas[0], rango_fechas[0]))
escuadria_param = None if escuadria_sel == "Todas" else escuadria_sel

df = cargar_datos(fecha_desde, fecha_hasta, escuadria_param, incluir_rechazo)

if df.empty:
    st.info("No hay datos de producción para los filtros seleccionados.")
    st.stop()

st.caption(f"Periodo: {fecha_desde:%d-%m-%Y} a {fecha_hasta:%d-%m-%Y}")

r = calcular_rendimiento_mensual(df)

st.metric("Rendimiento Total", f"{r.total:,.1f}%")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Rendimiento Turno 1", f"{r.turno_1:,.1f}%")
col2.metric("Rendimiento Turno 2", f"{r.turno_2:,.1f}%")
col3.metric("Rendimiento a Blank", f"{r.blank:,.1f}%")
col4.metric("Rendimiento a CTK", f"{r.ctk:,.1f}%")
col5.metric("% Bajo Espesor", f"{r.pct_bajo_espesor:,.1f}%")

st.divider()

col_izq, col_der = st.columns([3, 1])
with col_izq:
    st.subheader("Rendimiento diario")
    serie = serie_diaria_rendimiento(df)
    st.altair_chart(charts.rendimiento_diario(serie), width="stretch")
with col_der:
    st.subheader("Por Asignación")
    st.metric("Producto Principal", f"{r.producto_principal:,.1f}%", help="Acumulado del periodo")
    st.metric("Co-Producto Principal", f"{r.co_producto_principal:,.1f}%", help="Acumulado del periodo")
    st.metric("Co-Producto Secundario", f"{r.co_producto_secundario:,.1f}%", help="Acumulado del periodo")
    st.metric("Recuperación", f"{r.recuperacion:,.1f}%", help="Acumulado del periodo")
