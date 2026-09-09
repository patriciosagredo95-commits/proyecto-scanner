"""Constantes de layout de los archivos Excel y mapeos de negocio.

Todas las posiciones fueron verificadas manualmente contra los archivos reales
de ejemplo (RUN_2633, RUN_2841, RUN_2843, RUN_2845) y contra un escaneo completo
de los 688 archivos RUN_*.xlsx reales en "Run 2026/**".
"""

import re

# --- Turno ---
TURNO_DIA = 1
TURNO_NOCHE = 2
TURNO_TARDE = 3
TURNO_NUMERO_A_TEXTO = {TURNO_DIA: "Día", TURNO_NOCHE: "Noche", TURNO_TARDE: "Tarde"}
_TURNO_TEXTO_EXACTO = {"día": TURNO_DIA, "dia": TURNO_DIA, "noche": TURNO_NOCHE, "tarde": TURNO_TARDE}
_TURNO_PRIMERA_LETRA = {"d": TURNO_DIA, "n": TURNO_NOCHE, "t": TURNO_TARDE}


def normalizar_turno(texto: str | None) -> int | None:
    """Normaliza el texto de Turno (tabla izquierda del archivo RUN) a 1/2/3.

    Algunos archivos reales traen el texto con un caracter mal codificado
    (ej. 'D�a' en vez de 'Día', ~67 casos entre los 688 archivos reales) que no
    matchea una comparación exacta -- por eso el fallback usa solo la primera
    letra alfabética del texto (D/N/T), suficiente para distinguir los 3 turnos
    reales sin ambigüedad."""
    if not texto:
        return None
    texto_norm = texto.strip().lower()
    if texto_norm in _TURNO_TEXTO_EXACTO:
        return _TURNO_TEXTO_EXACTO[texto_norm]
    match = re.search(r"[a-záéíóúñ]", texto_norm)
    if match:
        return _TURNO_PRIMERA_LETRA.get(match.group(0))
    return None


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

# --- Archivos RUN: bloque "Total" (resumen del run completo, filas 18-91 de
# la columna A) -- a diferencia del bloque de metadata de arriba (etiqueta en
# columna A, valor en columna B), acá el layout es etiqueta/unidad/valor en
# columnas A/B/C. Solo se usa "Cortes" (fila 29, sin unidad en B, valor en C)
# -- verificado en los 354 archivos RUN reales no-Defects de "Run 2026/**".
RUN_TOTAL_CORTES_FILA = 29
RUN_TOTAL_CORTES_ETIQUETA = "Cortes"
RUN_TOTAL_COL_VALOR = 3

# --- Archivos RUN: tabla "Productos" (lado derecho) ---
RUN_PRODUCTOS_FILA_HEADER = 2
RUN_PRODUCTOS_FILA_INICIO_DATOS = 3
RUN_PRODUCTOS_COL_INICIO = 5   # columna E
# La tabla ya no tiene un ancho fijo: se lee la fila de encabezados desde la
# columna E hasta la primera celda vacía, con este tope como protección ante
# una hoja corrupta que devuelva encabezados indefinidamente.
RUN_PRODUCTOS_ANCHO_MAX = 40

# Los encabezados se comparan normalizados: espacios/saltos de línea colapsados
# a un solo espacio y sin espacios al inicio/fin (el archivo real trae los
# encabezados con un salto de línea antes de la unidad y un espacio al final).
#
# NI el orden NI el conjunto de columnas son estables entre archivos reales:
# el scanner exporta las columnas que tenga configuradas en ese momento. A
# partir del 26-08-2026 los archivos traen 19 columnas (agregaron
# "Cantidad [ % ]") en vez de las 18 anteriores, y con otro orden. Por eso solo
# se exige que estén presentes las columnas que efectivamente se leen; el resto
# (conocidas o nuevas) se ignora.
RUN_PRODUCTOS_HEADERS_REQUERIDOS = [
    "Estado", "Nombre", "Calidad",
    "Volumen Nominal [ m³ ]", "Cantidad [ pcs ]",
    "Largo [ % ]", "Largo [ m ]", "Largo Máximo", "Largo Mínimo",
    "Largo Promedio [ m ]", "Volumen Nominal [ % ]", "Volumen [ m³ ]",
]

# Columnas que aparecen en los archivos reales pero que no se leen. Se listan
# solo como documentación del formato; su ausencia no impide la carga.
RUN_PRODUCTOS_HEADERS_IGNORADOS = [
    "Color", "Pateador", "Nom. Done [ abs. ]", "Hecho [ % ]",
    "Volumen [ % ]", "Cantidad [ % ]", "Priority",
]


# --- Clasificación automática por nombre de producto (ver ingest/clasificador.py) ---
# Prefijo del Nombre (antes del primer '_') -> Tipo. Prefijos no listados usan el
# prefijo tal cual (mayúsculas); prefijos puramente numéricos usan "CTK" (ver
# clasificador.py -- evidenciado en 32 nombres reales con forma de CTK sin su
# prefijo, ej. "20_5X68_1990_FLEJES_EXP").
TIPO_POR_PREFIJO = {"BL": "BLANK", "CTK": "CTK", "RR": "RECUP"}
PREFIJO_RECUPERACION = "RR"

ASIGNACION_PRODUCTO_PRINCIPAL = "PRODUCTO PRINCIPAL"
ASIGNACION_CO_PRODUCTO_PRINCIPAL = "CO-PRODUCTO PRINCIPAL"
ASIGNACION_CO_PRODUCTO_SECUNDARIO = "CO-PRODUCTO SECUNDARIO"
ASIGNACION_RECUPERACION = "RECUPERACIÓN"

# Patrón de escuadria dentro de un Nombre: espesor (con posible decimal
# separado por '_', ej. "20_5") + 'x'/'X' + ancho. Ej. "BL_20_5x143_Base" ->
# espesor "20_5" (=20.5), ancho "143".
ESCUADRIA_EN_NOMBRE_REGEX = re.compile(r"(\d+(?:_\d+)?)[xX](\d+)")
# Escuadria dentro del nombre de archivo (best-effort, solo para warning blando).
ESCUADRIA_EN_ARCHIVO_REGEX = re.compile(r"(\d+(?:[.,_]\d+)?)[xX](\d+)")
