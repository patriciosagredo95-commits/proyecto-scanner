import pandas as pd
import streamlit as st

from scanner_app.config import CAMPOS_ASIGNACION_TEXTO
from scanner_app.db import get_conn
from scanner_app.ingest import master_resolver, validator
from scanner_app.ingest.loader import ingest_run
from scanner_app.parsing.filename import parse_filename
from scanner_app.parsing.run_file import parse_run_file
from scanner_app.repository import master_repo

st.title("Cargar archivo(s) RUN")
st.caption(
    "Suba uno o más archivos RUN_XXXX--FECHA--ESCUADRIA-DESCRIPCION.xlsx exportados por el scanner."
)

conn = get_conn()

st.session_state.setdefault("cargar_run__forzar", set())
st.session_state.setdefault("cargar_run__asignaciones", {})
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

        permitir_duplicado = nombre_parseado.run_numero in st.session_state["cargar_run__forzar"]
        resultado = validator.validar_run(s, nombre_parseado, archivo_parseado, permitir_duplicado=permitir_duplicado)
        parseados[archivo.name] = {
            "nombre_parseado": nombre_parseado,
            "archivo_parseado": archivo_parseado,
            "resultado": resultado,
        }

for nombre_archivo, mensaje in errores_parseo.items():
    st.error(f"**{nombre_archivo}**: {mensaje}")

if not parseados:
    st.stop()

# --- Nombres nuevos: consolidar entre todos los archivos válidos ---
with conn.session as s:
    nombres_nuevos_por_archivo = {
        nombre_archivo: master_resolver.nombres_nuevos(s, info["archivo_parseado"].productos)
        for nombre_archivo, info in parseados.items()
    }
todos_los_nuevos = sorted({n for lista in nombres_nuevos_por_archivo.values() for n in lista})
faltan_por_resolver = [n for n in todos_los_nuevos if n not in st.session_state["cargar_run__asignaciones"]]

if faltan_por_resolver:
    st.subheader(f"Asignación manual requerida ({len(faltan_por_resolver)} producto(s) nuevo(s))")
    st.caption(
        "Estos nombres de producto no existen todavía en la tabla maestra. "
        "Complete su clasificación una sola vez; quedará guardada para futuras cargas."
    )
    with conn.session as s:
        valores_sugeridos = {campo: master_repo.get_valores_distintos(s, campo) for campo in CAMPOS_ASIGNACION_TEXTO}

    with st.form("form_asignacion_manual"):
        valores_formulario = {}
        for nombre in faltan_por_resolver:
            st.markdown(f"**{nombre}**")
            cols = st.columns(4)
            escuadria = cols[0].text_input("Escuadria", key=f"escuadria_{nombre}")
            espesor_mm = cols[1].number_input("Espesor [mm]", min_value=0.0, step=0.1, key=f"espesor_{nombre}")
            ancho_mm = cols[2].number_input("Ancho [mm]", min_value=0.0, step=0.1, key=f"ancho_{nombre}")
            largo_nominal_mm = cols[3].number_input("Largo nominal [mm]", min_value=0.0, step=1.0, key=f"largo_{nombre}")

            campos_texto = {}
            for campo in CAMPOS_ASIGNACION_TEXTO:
                fila = st.columns(2)
                opcion = fila[0].selectbox(
                    campo.replace("_", " ").title(),
                    ["", *valores_sugeridos.get(campo, [])],
                    key=f"{campo}_sel_{nombre}",
                )
                otro = fila[1].text_input("Otro (especifique)", key=f"{campo}_otro_{nombre}")
                campos_texto[campo] = otro.strip() if otro.strip() else (opcion or None)

            fila_pct = st.columns(2)
            pct_recuperacion = fila_pct[0].number_input(
                "% Recuperación", min_value=0.0, max_value=1.0, step=0.01, key=f"pct_{nombre}"
            )
            ancho_recuperacion = fila_pct[1].number_input(
                "Ancho Recuperación", min_value=0.0, step=1.0, key=f"anchorec_{nombre}"
            )

            valores_formulario[nombre] = {
                "escuadria": escuadria or None,
                "espesor_mm": espesor_mm or None,
                "ancho_mm": ancho_mm or None,
                "largo_nominal_mm": largo_nominal_mm or None,
                "pct_recuperacion": pct_recuperacion or None,
                "ancho_recuperacion": ancho_recuperacion or None,
                **campos_texto,
            }
            st.divider()

        if st.form_submit_button("Guardar asignaciones", type="primary"):
            st.session_state["cargar_run__asignaciones"].update(valores_formulario)
            st.rerun()
    st.stop()

# --- Preview + advertencias ---
st.subheader("Resumen de la carga")
hay_error_bloqueante = False
with conn.session as s:
    master_actual = master_repo.get_all(s).set_index("nombre").to_dict("index")

for nombre_archivo, info in parseados.items():
    nombre_parseado = info["nombre_parseado"]
    archivo_parseado = info["archivo_parseado"]
    resultado = info["resultado"]

    with st.container(border=True):
        st.markdown(f"**{nombre_archivo}** — RUN_{nombre_parseado.run_numero}, {nombre_parseado.fecha}")

        if resultado.errores:
            for error in resultado.errores:
                st.error(error)
            if "Ya existe una carga previa" in " ".join(resultado.errores):
                if st.button("Forzar recarga", key=f"forzar_{nombre_archivo}"):
                    _dialogo_forzar_recarga(nombre_parseado.run_numero)
            hay_error_bloqueante = True
            continue

        for advertencia in resultado.advertencias:
            st.warning(advertencia)

        productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]]
        nombres_incluidos = productos_incluidos["nombre"].unique().tolist()
        master_combinado = {**master_actual, **st.session_state["cargar_run__asignaciones"]}
        advertencias_esc = validator.advertencias_escuadria(nombre_parseado, nombres_incluidos, master_combinado)
        for advertencia in advertencias_esc:
            st.warning(advertencia)

        excluidas = len(archivo_parseado.productos) - len(productos_incluidos)
        st.caption(
            f"{len(productos_incluidos)} fila(s) incluida(s), {excluidas} excluida(s) "
            f"(inactivas o cantidad 0). {'Es una corrida de RECHAZO.' if nombre_parseado.es_rechazo else ''}"
        )
        st.dataframe(
            productos_incluidos[
                ["nombre", "cantidad_pcs", "volumen_nominal_m3", "volumen_nominal_pct",
                 "largo_m", "largo_promedio_m"]
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
            nombre_parseado = info["nombre_parseado"]
            archivo_parseado = info["archivo_parseado"]
            asignaciones_de_este_archivo = {
                nombre: st.session_state["cargar_run__asignaciones"][nombre]
                for nombre in nombres_nuevos_por_archivo[nombre_archivo]
            }
            try:
                run_id = ingest_run(
                    s,
                    nombre_parseado,
                    archivo_parseado,
                    asignaciones_de_este_archivo,
                    forzar_recarga=nombre_parseado.run_numero in st.session_state["cargar_run__forzar"],
                )
                s.commit()
                resultados.append((nombre_archivo, "OK", f"run_id={run_id}"))
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                resultados.append((nombre_archivo, "ERROR", str(exc)))

    for nombre_archivo, estado, detalle in resultados:
        (st.success if estado == "OK" else st.error)(f"{nombre_archivo}: {estado} ({detalle})")

    st.cache_data.clear()
    st.session_state["cargar_run__asignaciones"] = {}
    st.session_state["cargar_run__forzar"] = set()
    st.session_state["cargar_run__uploader_key"] += 1

    if any(estado == "OK" for _, estado, _ in resultados):
        if st.button("Ir al Dashboard", icon=":material/dashboard:"):
            st.switch_page("app_pages/dashboard.py")
