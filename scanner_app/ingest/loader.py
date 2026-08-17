"""Orquesta la escritura completa de un RUN ya validado: clasificación
automática (ver ingest/clasificador.py), upsert en la tabla maestra e
inserción del registro de run y de sus production_facts.

Este módulo NO gestiona transacciones (no llama commit/rollback) -- el
llamador es responsable de envolver ingest_run en una transacción:
  - Desde la app Streamlit: `with conn.session as s: loader.ingest_run(s, ...); s.commit()`
  - Desde scripts/seed_inicial.py: `with engine.begin() as conn: loader.ingest_run(conn, ...)`
Así, si cualquier paso falla, no queda un `run_numero` a medio insertar
bloqueando un reintento futuro por la constraint UNIQUE.
"""

from scanner_app.config import normalizar_turno
from scanner_app.ingest.clasificador import clasificar_run
from scanner_app.parsing.filename import NombreArchivoRun
from scanner_app.parsing.run_file import ArchivoRunParseado
from scanner_app.repository import facts_repo, master_repo, runs_repo

_COLUMNAS_FACTS_RUN = [
    "run_id", "fuente", "nombre", "fecha", "turno", "es_rechazo",
    "escuadria", "espesor_mm", "ancho_mm", "calidad", "tipo", "asignacion",
    "destino_recuperacion", "volumen_nominal_m3", "largo_pct", "cantidad_pcs",
    "largo_m", "largo_promedio_m", "largo_maximo", "largo_minimo", "volumen_nominal_pct",
]

_COLUMNAS_MAESTRA = [
    "nombre", "escuadria", "espesor_mm", "ancho_mm", "calidad", "tipo",
    "asignacion", "destino_recuperacion", "fecha_referencia",
]


def ingest_run(
    conn,
    nombre_parseado: NombreArchivoRun,
    archivo_parseado: ArchivoRunParseado,
    forzar_recarga: bool = False,
) -> int:
    """Devuelve el id del run insertado. RUN/Fecha/Turno se toman de la
    metadata interna del archivo (tabla izquierda) -- ya no del nombre de
    archivo, que solo aporta señales blandas (escuadria/rechazo, ver
    parsing/filename.py)."""
    metadata = archivo_parseado.metadata

    run_numero = metadata.run_numero_interno
    if metadata.comienzo is None:
        raise ValueError("No se pudo determinar la fecha de comienzo del run (campo 'Comienzo' vacío).")
    fecha = metadata.comienzo.date()
    turno = normalizar_turno(metadata.turno_texto)
    if turno is None:
        raise ValueError(f"No se pudo determinar el turno a partir del valor interno '{metadata.turno_texto}'.")

    if forzar_recarga:
        runs_repo.delete_run_cascade(conn, run_numero)

    productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]].copy()
    nombres_unicos = productos_incluidos["nombre"].unique().tolist()
    nombres_nuevos = set(nombres_unicos) - master_repo.existen_nombres(conn, nombres_unicos)

    clasificados = clasificar_run(productos_incluidos, nombre_parseado.escuadria_archivo)

    maestra = clasificados.drop_duplicates(subset="nombre", keep="last")[
        ["nombre", "escuadria", "espesor_mm", "ancho_mm", "calidad", "tipo", "asignacion", "destino_recuperacion"]
    ].copy()
    maestra["fecha_referencia"] = fecha
    master_repo.bulk_upsert(conn, maestra[_COLUMNAS_MAESTRA])

    registro_run = {
        "run_numero": run_numero,
        "nombre_archivo": nombre_parseado.nombre_archivo,
        "fecha": fecha,
        "turno": turno,
        "escuadria_archivo": nombre_parseado.escuadria_archivo,
        "es_rechazo": nombre_parseado.es_rechazo,
        "operador": metadata.operador,
        "hora_comienzo": metadata.comienzo,
        "hora_fin": metadata.fin,
        "cantidad_total_pcs": int(productos_incluidos["cantidad_pcs"].sum()) if len(productos_incluidos) else 0,
        "largo_total_m": float(productos_incluidos["largo_m"].sum()) if len(productos_incluidos) else 0.0,
        "volumen_total_m3": float(productos_incluidos["volumen_m3"].sum()) if len(productos_incluidos) else 0.0,
        "volumen_nominal_total_m3": float(productos_incluidos["volumen_nominal_m3"].sum()) if len(productos_incluidos) else 0.0,
        "total_cortes": metadata.total_cortes,
        "filas_activas": int(len(productos_incluidos)),
        "filas_excluidas": int(len(archivo_parseado.productos) - len(productos_incluidos)),
        "productos_nuevos": len(nombres_nuevos),
    }
    run_id = runs_repo.insert_run(conn, registro_run)

    facts = clasificados.copy()
    facts["run_id"] = run_id
    facts["fuente"] = "run"
    facts["fecha"] = fecha
    facts["turno"] = turno
    facts["es_rechazo"] = nombre_parseado.es_rechazo
    facts["largo_pct"] = facts["largo_pct"] / 100
    facts["volumen_nominal_pct"] = facts["volumen_nominal_pct"] / 100
    facts_repo.bulk_insert_facts(conn, facts[_COLUMNAS_FACTS_RUN])

    return run_id
