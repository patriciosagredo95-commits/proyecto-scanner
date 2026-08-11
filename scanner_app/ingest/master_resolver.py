"""Detección de nombres de producto nuevos (no presentes en master_products)
dentro de las filas incluidas de un archivo RUN."""

import pandas as pd

from scanner_app.repository import master_repo


def nombres_incluidos(productos: pd.DataFrame) -> list[str]:
    return sorted(productos.loc[productos["incluido"], "nombre"].unique().tolist())


def nombres_nuevos(conn, productos: pd.DataFrame) -> list[str]:
    """Nombres de producto (entre los incluidos) que no existen todavía en la
    tabla maestra y requieren el formulario de asignación manual."""
    candidatos = nombres_incluidos(productos)
    existentes = master_repo.existen_nombres(conn, candidatos)
    return [nombre for nombre in candidatos if nombre not in existentes]
