#!/usr/bin/env python
"""Aplica el esquema, carga el histórico ('Base de datos Scanner.xlsx') y,
opcionalmente, los RUN_*.xlsx de ejemplo, en una base de datos PostgreSQL.

Uso:
    python scripts/seed_inicial.py --database-url postgresql+psycopg2://... \
        --incluir-runs-ejemplo --no-interactive

Es un script CLI independiente de st.secrets -- recibe la URL de conexión por
argumento o por la variable de entorno DATABASE_URL, no depende del runtime
de Streamlit. Reusa exactamente el mismo pipeline (parsing/ingest) que usará
la app, para validar que funciona de punta a punta.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner_app.config import CAMPOS_ASIGNACION_TEXTO  # noqa: E402
from scanner_app.ingest import master_resolver, validator  # noqa: E402
from scanner_app.ingest.loader import ingest_run  # noqa: E402
from scanner_app.parsing.filename import parse_filename  # noqa: E402
from scanner_app.parsing.historico_file import (  # noqa: E402
    build_facts_desde_historico,
    build_master_desde_historico,
    load_historico,
)
from scanner_app.parsing.run_file import parse_run_file  # noqa: E402
from scanner_app.repository import facts_repo, master_repo, runs_repo  # noqa: E402

_CAMPOS_MAESTRA_PLACEHOLDER = [
    "escuadria", "espesor_mm", "ancho_mm", "largo_nominal_mm",
    "destino", "tipo", "asignacion", "destino_recuperacion",
    "pct_recuperacion", "ancho_recuperacion", "obs_ancho", "obs_espesor",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="URL de conexión SQLAlchemy (ej. postgresql+psycopg2://user:pass@host/db). "
        "Si se omite, se usa la variable de entorno DATABASE_URL.",
    )
    parser.add_argument(
        "--proyecto-dir",
        default=str(Path(__file__).resolve().parent.parent),
        help="Carpeta donde están 'Base de datos Scanner.xlsx' y los RUN_*.xlsx.",
    )
    parser.add_argument(
        "--historico",
        default="Base de datos Scanner.xlsx",
        help="Nombre del archivo histórico dentro de --proyecto-dir.",
    )
    parser.add_argument(
        "--incluir-runs-ejemplo",
        action="store_true",
        help="Además del histórico, carga los RUN_*.xlsx encontrados en --proyecto-dir.",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Para nombres nuevos detectados en los RUN de ejemplo: crea un registro "
        "placeholder con pendiente_revision=True en vez de pedir los datos por consola.",
    )
    return parser.parse_args()


def aplicar_schema(engine) -> None:
    schema_sql = (Path(__file__).resolve().parent.parent / "scanner_app" / "schema.sql").read_text(encoding="utf-8")
    # Se ejecuta el archivo completo en una sola llamada (protocolo simple de
    # psycopg2, sin parámetros bindeados) en vez de partir por ";" -- partir
    # a mano es frágil apenas un comentario SQL contiene un punto y coma.
    with engine.begin() as conn:
        conn.exec_driver_sql(schema_sql)
    print("[schema] schema.sql aplicado.")


def cargar_historico(engine, ruta_historico: Path) -> None:
    with engine.begin() as conn:
        ya_cargado = conn.execute(
            text("SELECT count(*) FROM production_facts WHERE fuente = 'historico'")
        ).scalar_one()
    if ya_cargado > 0:
        print(f"[historico] Ya hay {ya_cargado} filas históricas cargadas, se omite (idempotente).")
        return

    df_historico = load_historico(ruta_historico)
    df_maestra = build_master_desde_historico(df_historico)
    df_facts = build_facts_desde_historico(df_historico)

    with engine.begin() as conn:
        master_repo.bulk_upsert(conn, df_maestra)
        facts_repo.bulk_insert_facts(conn, df_facts)

    print(
        f"[historico] {len(df_historico)} filas históricas cargadas "
        f"({len(df_maestra)} nombres únicos en la tabla maestra)."
    )


def _pedir_asignacion_por_consola(nombre: str) -> dict:
    print(f"\nProducto nuevo: '{nombre}' -- ingrese los valores de asignación (Enter para dejar vacío):")
    datos = {}
    for campo in _CAMPOS_MAESTRA_PLACEHOLDER:
        valor = input(f"  {campo}: ").strip()
        datos[campo] = valor if valor else None
    return datos


def cargar_runs_ejemplo(engine, proyecto_dir: Path, no_interactive: bool) -> None:
    archivos_run = sorted(proyecto_dir.glob("RUN_*.xlsx"))
    if not archivos_run:
        print("[runs] No se encontraron archivos RUN_*.xlsx en la carpeta del proyecto.")
        return

    cargados, omitidos, con_error = 0, 0, 0
    for ruta in archivos_run:
        try:
            nombre_parseado = parse_filename(ruta.name)
        except ValueError as exc:
            print(f"[runs] ERROR parseando nombre de archivo '{ruta.name}': {exc}")
            con_error += 1
            continue

        with engine.begin() as conn:
            if runs_repo.exists_run_numero(conn, nombre_parseado.run_numero):
                print(f"[runs] RUN_{nombre_parseado.run_numero} ya existe, se omite (idempotente).")
                omitidos += 1
                continue

            try:
                archivo_parseado = parse_run_file(ruta)
            except ValueError as exc:
                print(f"[runs] ERROR parseando contenido de '{ruta.name}': {exc}")
                con_error += 1
                continue

            resultado = validator.validar_run(conn, nombre_parseado, archivo_parseado, permitir_duplicado=True)
            if not resultado.es_valido:
                print(f"[runs] '{ruta.name}' inválido: {resultado.errores}")
                con_error += 1
                continue
            for advertencia in resultado.advertencias:
                print(f"[runs] Advertencia en '{ruta.name}': {advertencia}")

            nuevos = master_resolver.nombres_nuevos(conn, archivo_parseado.productos)
            asignaciones_manuales = {}
            if nuevos and no_interactive:
                for nombre in nuevos:
                    master_repo.upsert(
                        conn,
                        {
                            "nombre": nombre,
                            **{campo: None for campo in _CAMPOS_MAESTRA_PLACEHOLDER},
                            "fecha_referencia": nombre_parseado.fecha,
                            "origen": "manual",
                            "pendiente_revision": True,
                        },
                    )
                print(f"[runs] '{ruta.name}': {len(nuevos)} producto(s) nuevo(s) creados como pendiente_revision.")
            elif nuevos:
                for nombre in nuevos:
                    asignaciones_manuales[nombre] = _pedir_asignacion_por_consola(nombre)

            run_id = ingest_run(conn, nombre_parseado, archivo_parseado, asignaciones_manuales)
            print(f"[runs] '{ruta.name}' cargado como run_id={run_id}.")
            cargados += 1

    print(f"[runs] Resumen: {cargados} cargados, {omitidos} omitidos (duplicados), {con_error} con error.")


def main() -> None:
    args = parse_args()
    if not args.database_url:
        print("Error: falta --database-url (o la variable de entorno DATABASE_URL).", file=sys.stderr)
        sys.exit(1)

    proyecto_dir = Path(args.proyecto_dir)
    ruta_historico = proyecto_dir / args.historico
    if not ruta_historico.exists():
        print(f"Error: no se encontró el archivo histórico en '{ruta_historico}'.", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(args.database_url)

    aplicar_schema(engine)
    cargar_historico(engine, ruta_historico)

    if args.incluir_runs_ejemplo:
        cargar_runs_ejemplo(engine, proyecto_dir, args.no_interactive)

    with engine.begin() as conn:
        total_facts = conn.execute(text("SELECT count(*) FROM production_facts")).scalar_one()
        total_master = conn.execute(text("SELECT count(*) FROM master_products")).scalar_one()
        total_pendientes = conn.execute(
            text("SELECT count(*) FROM master_products WHERE pendiente_revision")
        ).scalar_one()
        total_runs = conn.execute(text("SELECT count(*) FROM runs")).scalar_one()

    print(
        "\n=== Resumen final ===\n"
        f"production_facts: {total_facts}\n"
        f"master_products:  {total_master} ({total_pendientes} pendientes de revisión)\n"
        f"runs:             {total_runs}"
    )


if __name__ == "__main__":
    main()
