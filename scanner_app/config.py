"""Constantes de layout de los archivos Excel y mapeos de negocio.

Todas las posiciones fueron verificadas manualmente contra los archivos reales
de ejemplo (RUN_2633, RUN_2841, RUN_2843, RUN_2845 y "Base de datos Scanner.xlsx").
"""

# --- Turno ---
TURNO_DIA = 1
TURNO_NOCHE = 2
TURNO_TEXTO_A_NUMERO = {"día": TURNO_DIA, "dia": TURNO_DIA, "noche": TURNO_NOCHE}
TURNO_NUMERO_A_TEXTO = {TURNO_DIA: "Día", TURNO_NOCHE: "Noche"}

# --- "Base de datos Scanner.xlsx": headers exactos de la hoja "Hoja1", fila 1 ---
HISTORICO_HOJA = "Hoja1"
HISTORICO_HEADERS = [
    "Escuadria", "Espesor", "Ancho", "Largo", "Turno ", "Fecha",
    "Destino Origen", "Destino", "Tipo", "Asignación", "Destino Recuperación",
    "% Recuperación", "Ancho Recuperación", "Obs Ancho", "Obs Espesor", "Nombre",
    "Volumen Nominal\n[ m³ ] ", "Largo\n[ % ] ", "Cantidad\n[ pcs ] ", "Largo\n[ m ] ",
    "Largo Promedio\n[ m ] ", "Volumen Nominal\n[ % ] ", "REND LN %", "REND VOL N %",
]

# --- Archivos RUN: bloque de metadata (columna A = etiqueta, columna B = valor) ---
# Posiciones fijas (1-indexed). Antes de leer, se valida que la etiqueta en
# columna A de esa fila coincida con lo esperado; si no, se hace un fallback
# de escaneo completo de columna A buscando la etiqueta (ver parsing/run_file.py).
# Nota: la etiqueta "Producción" se repite en las filas 3 y 5 -- por eso no se
# puede usar un escaneo genérico "primera fila con esta etiqueta" como método
# primario, se ancla a la posición de fila 3 específicamente.
RUN_META_FILAS = {
    "run_numero": (3, "Producción"),
    "estado": (4, "Estado"),
    "operador": (8, "Operador"),
    "turno": (9, "Turno"),
    "comienzo": (13, "Comienzo"),
    "fin": (14, "Fin"),
}
RUN_META_COL_ETIQUETA = 1
RUN_META_COL_VALOR = 2

# --- Archivos RUN: tabla "Productos" (lado derecho) ---
RUN_PRODUCTOS_FILA_HEADER = 2
RUN_PRODUCTOS_FILA_INICIO_DATOS = 3
RUN_PRODUCTOS_COL_INICIO = 5   # columna E
RUN_PRODUCTOS_COL_FIN = 22     # columna V

# Headers exactos esperados en la tabla Productos (fila 2, columnas E:V)
RUN_PRODUCTOS_HEADERS = [
    "Estado", "Color", "Nombre", "Calidad", "Pateador",
    "Volumen Nominal\n[ m³ ] ", "Volumen\n[ % ] ", "Cantidad\n[ pcs ] ",
    "Nom. Done\n[ abs. ] ", "Hecho\n[ % ] ", "Largo\n[ % ] ", "Volumen\n[ m³ ] ",
    "Largo\n[ m ] ", "Largo Máximo", "Largo Mínimo", "Largo Promedio\n[ m ] ",
    "Volumen Nominal\n[ % ] ", "Priority",
]

RUN_PRODUCTOS_ESTADO_ACTIVO = "Activo"

# --- Nombre de archivo: RUN_XXXX--YYYY-MM-DD--ESCUADRIA-DESCRIPCION[-TURNO-DIA|-TURNO-NOCHE][-RECHAZO].xlsx ---
FILENAME_REGEX = r"^RUN_(?P<run_numero>\d+)--(?P<fecha>\d{4}-\d{2}-\d{2})--(?P<resto>.+)\.xlsx$"

# --- Valores permitidos para los campos de asignación en la tabla maestra ---
# Se usan como opciones sugeridas (+ "Otro") en el formulario de asignación manual,
# poblados dinámicamente con los valores DISTINCT ya presentes en master_products.
CAMPOS_ASIGNACION_TEXTO = [
    "destino", "tipo", "asignacion",
    "destino_recuperacion", "obs_ancho", "obs_espesor",
]
