"""Acceso a la conexión de base de datos dentro de la app Streamlit.

Solo se usa desde app_pages/*. El resto de scanner_app/ (parsing, ingest,
repository) recibe una conexión/engine SQLAlchemy como parámetro y no depende
de Streamlit, para poder reutilizarse desde scripts/seed_inicial.py.
"""

import streamlit as st
from streamlit.connections import SQLConnection


def get_conn() -> SQLConnection:
    """Conexión cacheada por Streamlit (st.connection ya cachea internamente,
    no envolver en @st.cache_resource)."""
    return st.connection("postgresql", type="sql")
