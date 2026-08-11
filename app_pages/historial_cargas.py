import streamlit as st

from scanner_app.db import get_conn
from scanner_app.repository import runs_repo

st.title("Historial de Cargas")

conn = get_conn()
with conn.session as s:
    df = runs_repo.list_runs(s, limite=500)

if df.empty:
    st.info("Todavía no se ha cargado ningún RUN.")
    st.stop()

st.caption(f"{len(df)} carga(s) registradas.")
st.dataframe(
    df,
    width="stretch",
    hide_index=True,
    column_config={
        "es_rechazo": st.column_config.CheckboxColumn("¿Rechazo?"),
        "run_numero": st.column_config.NumberColumn("N° RUN"),
    },
)
