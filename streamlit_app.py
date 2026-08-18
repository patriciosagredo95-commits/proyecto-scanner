import streamlit as st

st.set_page_config(page_title="Scanner Maderera", layout="wide")

paginas = [
    st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("app_pages/rendimiento_mensual.py", title="Rendimiento Mensual", icon=":material/insights:"),
    st.Page("app_pages/indice_rendimiento.py", title="Indice de Rendimiento", icon=":material/timeline:"),
    st.Page("app_pages/cargar_run.py", title="Cargar RUN", icon=":material/upload_file:"),
    st.Page("app_pages/tabla_maestra.py", title="Tabla Maestra", icon=":material/table_view:"),
    st.Page("app_pages/historial_cargas.py", title="Historial de Cargas", icon=":material/history:"),
]

navegacion = st.navigation(paginas)
navegacion.run()
