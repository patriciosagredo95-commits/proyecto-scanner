from datetime import date, timedelta

import streamlit as st

from scanner_app.dashboard import charts, kpis
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
    turno_sel = st.selectbox("Turno", ["Ambos", "Día", "Noche"])
    incluir_rechazo = st.checkbox("Incluir corridas de Rechazo", value=True)
    agrupacion = st.segmented_control("Agrupar por", ["Día", "Semana", "Mes"], default="Día")
    if st.button("Actualizar ahora", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()

fecha_desde, fecha_hasta = (rango_fechas if len(rango_fechas) == 2 else (rango_fechas[0], rango_fechas[0]))
escuadria_param = None if escuadria_sel == "Todas" else escuadria_sel
turno_param = {"Día": 1, "Noche": 2}.get(turno_sel)

df = cargar_datos(fecha_desde, fecha_hasta, escuadria_param, turno_param, incluir_rechazo)

if df.empty:
    st.info("No hay datos de producción para los filtros seleccionados.")
    st.stop()

resumen = kpis.calcular_kpis(df)

nombres_sin_escuadria = kpis.nombres_excluidos_de_rendimiento(df)
if nombres_sin_escuadria:
    st.warning(
        f"{len(nombres_sin_escuadria)} producto(s) sin escuadria asignada quedan excluidos del cálculo "
        "de **Rendimiento Vol. Nominal** (se agrupa por fecha + turno + escuadria) -- probablemente son "
        "productos 'pendientes de revisión' que faltan completar en Tabla Maestra: "
        + ", ".join(nombres_sin_escuadria)
    )

col1, col2, col3, col4, col5 = st.container(horizontal=True).columns(5)
col1.metric("Volumen Nominal [m³]", f"{resumen.volumen_nominal_m3:,.2f}")
col2.metric("Rendimiento Vol. Nominal [%]", f"{resumen.rendimiento_pct:,.1f}%")
col3.metric("Cantidad [pcs]", f"{resumen.cantidad_pcs:,}")
col4.metric("N° de RUNs", f"{resumen.num_runs:,}")
col5.metric("% Rechazo", f"{resumen.pct_rechazo:,.1f}%")

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
        st.altair_chart(charts.rendimiento_en_el_tiempo(df, agrupacion=agrupacion), width="stretch")

col_izq2, col_der2 = st.columns(2)
with col_izq2:
    with st.container(border=True):
        st.subheader("Distribución")
        dimension = st.selectbox(
            "Agrupar por", ["destino", "asignacion", "tipo"], key="dimension_distribucion"
        )
        st.altair_chart(charts.distribucion_por_dimension(df, dimension), width="stretch")
with col_der2:
    with st.container(border=True):
        st.subheader("Top productos por Volumen Nominal")
        st.altair_chart(charts.top_productos(df), width="stretch")

st.divider()
st.subheader("RUNs recientes")
with get_conn().session as s:
    df_runs = runs_repo.list_runs(s, limite=20)
st.dataframe(df_runs, width="stretch", hide_index=True)
