"""Orquesta la escritura completa de un RUN ya validado: upsert de nombres
nuevos en la tabla maestra, inserción del registro de run y de sus
production_facts.

Este módulo NO gestiona transacciones (no llama commit/rollback) -- el
llamador es responsable de envolver ingest_run en una transacción:
  - Desde la app Streamlit: `with conn.session as s: loader.ingest_run(s, ...); s.commit()`
  - Desde scripts/seed_inicial.py: `with engine.begin() as conn: loader.ingest_run(conn, ...)`
Así, si cualquier paso falla, no queda un `run_numero` a medio insertar
bloqueando un reintento futuro por la constraint UNIQUE.
"""

import pandas as pd

from scanner_app.parsing.filename import NombreArchivoRun
from scanner_app.parsing.run_file import ArchivoRunParseado
from scanner_app.repository import facts_repo, master_repo, runs_repo

_COLUMNAS_FACTS_RUN = [
    "run_id", "fuente", "nombre", "fecha", "turno", "es_rechazo",
    "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm",
    "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor",
    "volumen_nominal_m3", "largo_pct", "cantidad_pcs", "largo_m",
    "largo_promedio_m", "volumen_nominal_pct", "rend_ln_pct", "rend_vol_n_pct",
]


def ingest_run(
    conn,
    nombre_parseado: NombreArchivoRun,
    archivo_parseado: ArchivoRunParseado,
    asignaciones_manuales: dict[str, dict] | None = None,
    forzar_recarga: bool = False,
) -> int:
    """Devuelve el id del run insertado. `asignaciones_manuales` debe cubrir
    todos los nombres nuevos detectados por ingest.master_resolver antes de
    llamar a esta función (se valida explícitamente para no insertar
    production_facts huérfanos de una fila de master_products)."""
    asignaciones_manuales = asignaciones_manuales or {}

    if forzar_recarga:
        runs_repo.delete_run_cascade(conn, nombre_parseado.run_numero)

    productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]].copy()

    nombres_sin_resolver = set(productos_incluidos["nombre"]) - master_repo.existen_nombres(
        conn, productos_incluidos["nombre"].unique().tolist()
    ) - set(asignaciones_manuales.keys())
    if nombres_sin_resolver:
        raise ValueError(
            "Faltan asignaciones manuales para los siguientes nombres nuevos: "
            f"{sorted(nombres_sin_resolver)}"
        )

    for nombre, datos in asignaciones_manuales.items():
        registro = {
            "nombre": nombre,
            "escuadria": datos.get("escuadria"),
            "espesor_mm": datos.get("espesor_mm"),
            "ancho_mm": datos.get("ancho_mm"),
            "largo_nominal_mm": datos.get("largo_nominal_mm"),
            "destino": datos.get("destino"),
            "tipo": datos.get("tipo"),
            "asignacion": datos.get("asignacion"),
            "destino_recuperacion": datos.get("destino_recuperacion"),
            "pct_recuperacion": datos.get("pct_recuperacion"),
            "ancho_recuperacion": datos.get("ancho_recuperacion"),
            "obs_ancho": datos.get("obs_ancho"),
            "obs_espesor": datos.get("obs_espesor"),
            "fecha_referencia": nombre_parseado.fecha,
            "origen": "manual",
            "pendiente_revision": False,
        }
        master_repo.upsert(conn, registro)

    turno_final = nombre_parseado.turno_archivo
    if turno_final is None:
        from scanner_app.config import TURNO_TEXTO_A_NUMERO

        turno_final = TURNO_TEXTO_A_NUMERO.get(
            (archivo_parseado.metadata.turno_texto or "").strip().lower()
        )
    if turno_final is None:
        raise ValueError("No se pudo determinar el turno (ni desde el nombre de archivo ni desde el contenido).")

    registro_run = {
        "run_numero": nombre_parseado.run_numero,
        "nombre_archivo": nombre_parseado.nombre_archivo,
        "fecha": nombre_parseado.fecha,
        "turno": turno_final,
        "escuadria_archivo": nombre_parseado.escuadria_archivo,
        "descripcion_archivo": nombre_parseado.descripcion_archivo,
        "es_rechazo": nombre_parseado.es_rechazo,
        "operador": archivo_parseado.metadata.operador,
        "hora_comienzo": archivo_parseado.metadata.comienzo,
        "hora_fin": archivo_parseado.metadata.fin,
        "cantidad_total_pcs": int(productos_incluidos["cantidad_pcs"].sum()) if len(productos_incluidos) else 0,
        "largo_total_m": float(productos_incluidos["largo_m"].sum()) if len(productos_incluidos) else 0.0,
        "volumen_total_m3": float(productos_incluidos["volumen_m3"].sum()) if len(productos_incluidos) else 0.0,
        "volumen_nominal_total_m3": float(productos_incluidos["volumen_nominal_m3"].sum()) if len(productos_incluidos) else 0.0,
        "filas_activas": int(len(productos_incluidos)),
        "filas_excluidas": int(len(archivo_parseado.productos) - len(productos_incluidos)),
        "productos_nuevos": len(asignaciones_manuales),
    }
    run_id = runs_repo.insert_run(conn, registro_run)

    # Foto de la clasificación VIGENTE en este momento -- queda fija en la fila
    # de ahora en adelante, aunque después se edite el Nombre en la Tabla Maestra.
    clasificacion = master_repo.get_clasificacion_por_nombres(conn, productos_incluidos["nombre"].unique().tolist())
    facts = productos_incluidos.merge(clasificacion, on="nombre", how="left")
    facts["run_id"] = run_id
    facts["fuente"] = "run"
    facts["fecha"] = nombre_parseado.fecha
    facts["turno"] = turno_final
    facts["es_rechazo"] = nombre_parseado.es_rechazo
    facts["rend_ln_pct"] = facts["largo_pct"] / 100
    facts["rend_vol_n_pct"] = facts["volumen_nominal_pct"] / 100
    facts_repo.bulk_insert_facts(conn, facts[_COLUMNAS_FACTS_RUN])

    return run_id
