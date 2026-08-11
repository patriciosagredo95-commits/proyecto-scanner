import pandas as pd
import streamlit as st

from scanner_app.db import get_conn
from scanner_app.repository import master_repo

st.title("Tabla Maestra de Asignación")
st.caption(
    "Clasificación por Nombre de producto (Escuadria, Destino, Tipo, Asignación, etc.) "
    "usada para resolver automáticamente cada carga de RUN. Los nombres 'pendientes de "
    "revisión' fueron creados sin datos completos y conviene completarlos aquí."
)

conn = get_conn()

with conn.session as s:
    df = master_repo.get_all(s)

if df.empty:
    st.info("La tabla maestra está vacía. Cargue primero el histórico con scripts/seed_inicial.py.")
    st.stop()

solo_pendientes = st.checkbox("Mostrar solo pendientes de revisión", value=bool(df["pendiente_revision"].any()))
df_mostrado = df[df["pendiente_revision"]] if solo_pendientes else df

st.caption(f"{len(df_mostrado)} de {len(df)} productos mostrados.")

columnas_no_editables = ["nombre", "origen", "creado_en", "actualizado_en"]
editado = st.data_editor(
    df_mostrado,
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
