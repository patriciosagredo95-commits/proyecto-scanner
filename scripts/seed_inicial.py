#!/usr/bin/env python
"""Aplica el esquema y carga los archivos RUN_*.xlsx reales (recursivo) en una
base de datos PostgreSQL. Ya no depende de 'Base de datos Scanner.xlsx' -- toda
la clasificación (Escuadria, Tipo, Asignación, Destino Recuperación, Calidad)
se deriva automáticamente del contenido de cada RUN (ver
scanner_app/ingest/clasificador.py).

Uso:
    # Reset completo (DESTRUCTIVO) + recarga de todo Run 2026/**:
    python scripts/seed_inicial.py --database-url postgresql+psycopg2://... --reset

    # Dry-run (sin tocar la base, solo valida que todo parsea/clasifica):
    python scripts/seed_inicial.py --dry-run

Es un script CLI independiente de st.secrets -- recibe la URL de conexión por
argumento o por la variable de entorno DATABASE_URL, no depende del runtime
de Streamlit. Reusa exactamente el mismo pipeline (parsing/ingest) que usará
la app, para validar que funciona de punta a punta.

Archivos "-Defects-" (334 de los 688 reales en Run 2026/**) no son RUN de
producción -- es un reporte distinto (códigos de defecto, sin tabla
"Productos") -- se excluyen por nombre antes de intentar parsearlos. Cuando
dos archivos comparten el mismo RUN interno (4 casos reales, duplicados/
reexportados), se conserva el primero por orden alfabético de ruta y el resto
se omite.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner_app.ingest import validator  # noqa: E402
from scanner_app.ingest.clasificador import clasificar_run  # noqa: E402
from scanner_app.ingest.loader import ingest_run  # noqa: E402
from scanner_app.parsing.filename import parse_filename  # noqa: E402
from scanner_app.parsing.run_file import parse_run_file  # noqa: E402
from scanner_app.repository import runs_repo  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="URL de conexión SQLAlchemy (ej. postgresql+psycopg2://user:pass@host/db). "
        "Si se omite, se usa la variable de entorno DATABASE_URL. No se requiere con --dry-run.",
    )
    parser.add_argument(
        "--run-dir",
        default=str(Path(__file__).resolve().parent.parent / "Run 2026"),
        help="Carpeta a recorrer recursivamente buscando RUN_*.xlsx.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="DESTRUCTIVO: borra production_facts, runs y master_products antes de aplicar "
        "el schema y recargar. schema.sql en sí NUNCA borra nada -- este flag es la única "
        "vía de reset, para que un re-run accidental sin --reset jamás pierda datos.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parsea y clasifica todos los archivos candidatos sin conectarse a la base ni escribir nada.",
    )
    return parser.parse_args()


def aplicar_schema(engine) -> None:
    schema_sql = (Path(__file__).resolve().parent.parent / "scanner_app" / "schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(schema_sql)
    print("[schema] schema.sql aplicado.")


def resetear(engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS production_facts, runs, master_products CASCADE")
    print("[reset] production_facts, runs y master_products eliminadas.")


def encontrar_archivos(run_dir: Path) -> list[Path]:
    if not run_dir.exists():
        return []
    return sorted(f for f in run_dir.glob("**/*.xlsx") if "defect" not in f.name.lower())


def cargar_runs(engine, archivos: list[Path], dry_run: bool) -> None:
    run_numero_a_archivo: dict[int, str] = {}
    cargados = omitidos = con_error = 0

    for ruta in archivos:
        nombre_parseado = parse_filename(ruta.name)
        try:
            archivo_parseado = parse_run_file(ruta)
        except ValueError as exc:
            print(f"[runs] ERROR parseando '{ruta.name}': {exc}")
            con_error += 1
            continue

        run_numero = archivo_parseado.metadata.run_numero_interno
        if run_numero in run_numero_a_archivo:
            print(f"[runs] RUN_{run_numero} ('{ruta.name}') duplica a '{run_numero_a_archivo[run_numero]}', se omite.")
            omitidos += 1
            continue
        run_numero_a_archivo[run_numero] = ruta.name

        if dry_run:
            try:
                productos_incluidos = archivo_parseado.productos.loc[archivo_parseado.productos["incluido"]]
                if productos_incluidos.empty:
                    raise ValueError("todas las filas tienen cantidad y/o volumen nominal 0")
                if archivo_parseado.metadata.comienzo is None:
                    raise ValueError("falta el campo 'Comienzo' en la metadata")
                from scanner_app.config import normalizar_turno

                if normalizar_turno(archivo_parseado.metadata.turno_texto) is None:
                    raise ValueError(f"turno no reconocido: {archivo_parseado.metadata.turno_texto!r}")
                clasificar_run(productos_incluidos, nombre_parseado.escuadria_archivo)
                cargados += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[runs] ERROR clasificando '{ruta.name}': {exc}")
                con_error += 1
            continue

        with engine.connect() as conn:
            if runs_repo.exists_run_numero(conn, run_numero):
                print(f"[runs] RUN_{run_numero} ya existe en la base, se omite.")
                omitidos += 1
                continue

            resultado = validator.validar_run(conn, nombre_parseado, archivo_parseado, permitir_duplicado=True)
            if not resultado.es_valido:
                print(f"[runs] '{ruta.name}' inválido: {resultado.errores}")
                con_error += 1
                continue
            for advertencia in resultado.advertencias:
                print(f"[runs] Advertencia en '{ruta.name}': {advertencia}")

            # commit/rollback explícitos (estilo "commit as you go" de
            # SQLAlchemy 2.0) -- si ingest_run falla a mitad de camino, hay
            # que hacer rollback antes de seguir con el próximo archivo (si se
            # atrapa la excepción DENTRO de un `with engine.begin()`, el
            # context manager no ve la excepción y comitea igual lo que
            # ingest_run ya haya escrito antes de fallar).
            try:
                run_id = ingest_run(conn, nombre_parseado, archivo_parseado)
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                print(f"[runs] ERROR cargando '{ruta.name}': {exc}")
                con_error += 1
                continue
            conn.commit()
            print(f"[runs] '{ruta.name}' cargado como run_id={run_id} (RUN_{run_numero}).")
            cargados += 1

    modo = "clasificados" if dry_run else "cargados"
    print(f"\n[runs] Resumen: {cargados} {modo}, {omitidos} omitidos (duplicados), {con_error} con error.")


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    archivos = encontrar_archivos(run_dir)
    print(f"[runs] {len(archivos)} archivo(s) candidatos (excluye '-Defects-') encontrados en '{run_dir}'.")

    if args.dry_run:
        cargar_runs(None, archivos, dry_run=True)
        return

    if not args.database_url:
        print("Error: falta --database-url (o la variable de entorno DATABASE_URL).", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(args.database_url)

    if args.reset:
        resetear(engine)
    aplicar_schema(engine)
    cargar_runs(engine, archivos, dry_run=False)

    with engine.begin() as conn:
        total_facts = conn.execute(text("SELECT count(*) FROM production_facts")).scalar_one()
        total_master = conn.execute(text("SELECT count(*) FROM master_products")).scalar_one()
        total_runs = conn.execute(text("SELECT count(*) FROM runs")).scalar_one()

    print(
        "\n=== Resumen final ===\n"
        f"production_facts: {total_facts}\n"
        f"master_products:  {total_master}\n"
        f"runs:             {total_runs}"
    )


if __name__ == "__main__":
    main()
