import pandas as pd
import streamlit as st

from scanner_app.db import get_conn
from scanner_app.repository import master_repo

st.title("Tabla Maestra de Asignación")
st.caption(
    "Clasificación por Nombre de producto (Escuadria, Tipo, Asignación, etc.), calculada "
    "automáticamente a partir del contenido de cada RUN cargado. Refleja siempre la última "
    "carga que incluyó ese Nombre -- una edición manual acá es un override temporal: se "
    "recalculará apenas se cargue un nuevo RUN que vuelva a incluir ese producto."
)

conn = get_conn()

with conn.session as s:
    df = master_repo.get_all(s)

if df.empty:
    st.info("La tabla maestra está vacía. Cargue primero archivos RUN en 'Cargar RUN'.")
    st.stop()

st.caption(f"{len(df)} producto(s).")

columnas_no_editables = ["nombre", "creado_en", "actualizado_en"]
editado = st.data_editor(
    df,
    key="editor_tabla_maestra",
    hide_index=True,
    num_rows="fixed",
    disabled=columnas_no_editables,
    width="stretch",
)


def _fila_a_registro(fila: pd.Series) -> dict:
    registro = {}
    for campo, valor in fila.to_dict().items():
        if campo in ("creado_en", "actualizado_en"):
            continue
        if isinstance(valor, float) and pd.isna(valor):
            valor = None
        elif hasattr(valor, "item"):
            valor = valor.item()
        registro[campo] = valor
    return registro


if st.button("Guardar cambios", type="primary", icon=":material/save:"):
    with conn.session as s:
        for _, fila in editado.iterrows():
            master_repo.upsert(s, _fila_a_registro(fila))
        s.commit()
    st.cache_data.clear()
    st.success("Cambios guardados.")
    st.rerun()
