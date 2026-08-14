import streamlit as st

from scanner_app.db import get_conn
from scanner_app.ingest import validator
from scanner_app.ingest.clasificador import clasificar_run
from scanner_app.ingest.loader import ingest_run
from scanner_app.parsing.filename import parse_filename
from scanner_app.parsing.run_file import parse_run_file

st.title("Cargar archivo(s) RUN")
st.caption(
    "Suba uno o más archivos RUN_*.xlsx exportados por el scanner. La clasificación "
    "(Escuadria, Tipo, Asignación, Destino Recuperación) se calcula automáticamente "
    "a partir del contenido del archivo -- no requiere completar nada a mano."
)

conn = get_conn()

st.session_state.setdefault("cargar_run__forzar", set())
st.session_state.setdefault("cargar_run__uploader_key", 0)


@st.dialog("Confirmar recarga")
def _dialogo_forzar_recarga(run_numero: int):
    st.warning(
        f"Ya existe una carga previa para RUN_{run_numero}. "
        "Forzar la recarga reemplazará por completo sus datos de producción."
    )
    col1, col2 = st.columns(2)
    if col1.button("Sí, forzar recarga", type="primary", width="stretch"):
        st.session_state["cargar_run__forzar"].add(run_numero)
        st.rerun()
    if col2.button("Cancelar", width="stretch"):
        st.rerun()


archivos = st.file_uploader(
    "Archivos RUN (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state['cargar_run__uploader_key']}",
)

if not archivos:
    st.stop()

# --- Parseo + validación de cada archivo ---
parseados = {}
errores_parseo = {}
with conn.session as s:
    for archivo in archivos:
        try:
            nombre_parseado = parse_filename(archivo.name)
            archivo_parseado = parse_run_file(archivo)
        except ValueError as exc:
            errores_parseo[archivo.name] = str(exc)
            continue

        run_numero = archivo_parseado.metadata.run_numero_interno
        permitir_duplicado = run_numero in st.session_state["cargar_run__forzar"]
        resultado = validator.validar_run(s, nombre_parseado, archivo_parseado, permitir_duplicado=permitir_duplicado)
        parseados[archivo.name] = {
            "nombre_parseado": nombre_parseado,
            "archivo_parseado": archivo_parseado,
            "run_numero": run_numero,
            "resultado": resultado,
        }

for nombre_archivo, mensaje in errores_parseo.items():
    st.error(f"**{nombre_archivo}**: {mensaje}")

if not parseados:
    st.stop()

# --- Preview + advertencias ---
st.subheader("Resumen de la carga")
hay_error_bloqueante = False

for nombre_archivo, info in parseados.items():
    nombre_parseado = info["nombre_parseado"]
    archivo_parseado = info["archivo_parseado"]
    resultado = info["resultado"]

    with st.container(border=True):
        st.markdown(f"**{nombre_archivo}** — RUN_{info['run_numero']}")

        if resultado.errores:
            for error in resultado.errores:
                st.error(error)
            if "Ya existe una carga previa" in " ".join(resultado.errores):
                if st.button("Forzar recarga", key=f"forzar_{nombre_archivo}"):
                    _dialogo_forzar_recarga(info["run_numero"])
            hay_error_bloqueante = True
            continue

        for advertencia in resultado.advertencias:
            st.warning(advertencia)

        productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]]
        clasificados = clasificar_run(productos_incluidos, nombre_parseado.escuadria_archivo)

        excluidas = len(archivo_parseado.productos) - len(productos_incluidos)
        st.caption(
            f"{len(productos_incluidos)} fila(s) incluida(s), {excluidas} excluida(s) "
            f"(cantidad y/o volumen nominal 0). {'Es una corrida de RECHAZO.' if nombre_parseado.es_rechazo else ''}"
        )
        st.dataframe(
            clasificados[
                ["nombre", "escuadria", "tipo", "asignacion", "destino_recuperacion",
                 "cantidad_pcs", "volumen_nominal_m3", "volumen_nominal_pct"]
            ],
            width="stretch",
            hide_index=True,
        )

if hay_error_bloqueante:
    st.info("Resuelva los errores marcados arriba (o fuerce la recarga) antes de confirmar.")

if not hay_error_bloqueante and st.button("Confirmar carga", type="primary", icon=":material/cloud_upload:"):
    resultados = []
    with conn.session as s:
        for nombre_archivo, info in parseados.items():
            try:
                run_id = ingest_run(
                    s,
                    info["nombre_parseado"],
                    info["archivo_parseado"],
                    forzar_recarga=info["run_numero"] in st.session_state["cargar_run__forzar"],
                )
                s.commit()
                resultados.append((nombre_archivo, "OK", f"run_id={run_id}"))
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                resultados.append((nombre_archivo, "ERROR", str(exc)))

    for nombre_archivo, estado, detalle in resultados:
        (st.success if estado == "OK" else st.error)(f"{nombre_archivo}: {estado} ({detalle})")

    st.cache_data.clear()
    st.session_state["cargar_run__forzar"] = set()
    st.session_state["cargar_run__uploader_key"] += 1

    if any(estado == "OK" for _, estado, _ in resultados):
        if st.button("Ir al Dashboard", icon=":material/dashboard:"):
            st.switch_page("app_pages/dashboard.py")
