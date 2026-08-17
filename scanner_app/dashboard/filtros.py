"""Selector de rango de fechas amigable, con presets rápidos en español.

st.date_input en modo rango tiene un bug de renderizado dentro de contenedores
angostos (como el sidebar): el calendario de dos meses se corta y no deja
navegar al mes siguiente. Por eso acá se usan presets + dos st.date_input de
un solo mes cada uno (modo "Personalizado"), que no tienen ese problema.
"""

from datetime import date, timedelta

import streamlit as st


def selector_rango_fechas(key_prefix: str, presets: dict[str, int | None], default: str) -> tuple[date, date]:
    """Presets (días atrás desde hoy; None = "este mes") + modo Personalizado."""
    hoy = date.today()
    preset = st.segmented_control(
        "Periodo", [*presets.keys(), "Personalizado"], default=default, key=f"{key_prefix}_preset"
    ) or default

    if preset == "Personalizado":
        col_desde, col_hasta = st.columns(2)
        fecha_desde = col_desde.date_input(
            "Desde", value=hoy - timedelta(days=presets[default] or 30),
            format="YYYY-MM-DD", key=f"{key_prefix}_desde",
        )
        fecha_hasta = col_hasta.date_input("Hasta", value=hoy, format="YYYY-MM-DD", key=f"{key_prefix}_hasta")
        return fecha_desde, fecha_hasta

    dias = presets[preset]
    if dias is None:
        return hoy.replace(day=1), hoy
    return hoy - timedelta(days=dias), hoy
