# Entrega Formal — Sistema de Informe Scanner

**Para:** Área de Operaciones
**De:** Patricio Sagredo — patricio.sagredo@glover.cl
**Fecha de entrega:** 9 de septiembre de 2026
**Estado:** En producción, operativo
**Acceso:** *(completar con la URL de la aplicación)*

---

## 1. Objeto de la entrega

Se entrega formalmente al Área de Operaciones el **Sistema de Informe Scanner**, una aplicación web que reemplaza el proceso manual de consolidación en planillas Excel de los archivos `RUN_*.xlsx` exportados por el scanner de la línea.

El sistema queda operativo, con el histórico cargado desde **15-12-2025 hasta 08-09-2026**, y disponible para uso diario del área sin intervención del área técnica.

---

## 2. Alcance de lo entregado

La aplicación se compone de seis módulos accesibles desde el menú lateral:

| Módulo | Función |
|---|---|
| **Dashboard** | Vista principal de producción y rendimiento, con filtros por período, escuadría y turno. |
| **Rendimiento Mensual** | Rendimiento por turno, por tipo (Blank / CTK) y por asignación, con la metodología del reporte histórico. |
| **Índice de Rendimiento** | Comparación Rendimiento Real vs. Meta histórica por escuadría. |
| **Cargar RUN** | Carga de uno o varios archivos del scanner desde el navegador, con vista previa y validación. |
| **Tabla Maestra** | Catálogo de productos con su clasificación (escuadría, tipo, asignación, destino de recuperación). |
| **Historial de Cargas** | Registro auditable de todas las cargas realizadas. |

Detrás de la aplicación hay una base de datos PostgreSQL única y centralizada, que constituye desde ahora la **fuente oficial de información de producción del scanner**.

---

## 3. Beneficios para Operaciones

### 3.1 Elimina la clasificación manual de productos

Anteriormente, cada nombre de producto nuevo obligaba a completar un formulario a mano para definir su escuadría, tipo y asignación. Hoy **toda la clasificación se calcula automáticamente** a partir del contenido del propio archivo del scanner: escuadría, tipo (BLANK / CTK / RECUP), asignación (Producto Principal, Co-Producto Principal, Co-Producto Secundario, Recuperación) y destino de recuperación.

El operador sube el archivo y confirma. No hay nada que completar a mano.

### 3.2 Un solo lugar con toda la información

Los 415 RUN del histórico están consolidados en una única base, consultable por cualquier persona del área desde el navegador. Se termina la dispersión de planillas, las versiones paralelas y la duda de cuál es el archivo válido.

### 3.3 Continuidad con el reporte histórico

El cálculo de rendimiento **replica la metodología del reporte mensual en Excel** que ya se utilizaba (promedio por lote Fecha + Turno + Escuadría). Esto permite comparar los resultados nuevos contra la serie histórica sin quiebre de criterio.

### 3.4 Indicadores disponibles de inmediato

Sin construir planillas, el área tiene a la vista:

- Volumen Nominal y Metros Lineales en el tiempo (por día, semana o mes)
- Rendimiento en el tiempo, y Rendimiento Real vs. Meta por escuadría
- Total de Cortes por RUN y su evolución
- Rendimiento por turno (1, 2 y 3) y por tipo de producto
- Distribución por asignación y por tipo
- Ranking de escuadrías por volumen y mix de asignación por escuadría
- **Producción y rendimiento por operador**
- Pareto de destino de la recuperación
- Porcentaje de rechazo sobre piezas

### 3.5 Control de calidad de la carga, antes de escribir

La carga no es a ciegas. Antes de confirmar, el sistema muestra la vista previa ya clasificada y aplica validaciones:

- **Bloquea duplicados:** si un RUN ya fue cargado, avisa y exige confirmación explícita para reemplazarlo.
- **Advierte inconsistencias:** si la escuadría del nombre del archivo no coincide con la de los productos reales, lo señala. Esto ya permitió detectar archivos mal nombrados.
- **Excluye filas vacías:** las líneas con cantidad o volumen en cero no contaminan las estadísticas.
- **Rechaza archivos con formato incorrecto** indicando exactamente qué columna falta.

### 3.6 Trazabilidad y auditoría

Cada carga queda registrada con fecha, archivo de origen, operador, filas incluidas y excluidas, y productos nuevos detectados. Además, la clasificación se guarda como una **foto del momento de la carga**: si más adelante un producto se reclasifica, el histórico ya informado no cambia retroactivamente.

### 3.7 Autonomía del área

La carga se realiza desde el navegador, con varios archivos a la vez, sin depender del área técnica y sin instalar nada en el computador.

---

## 4. Estado de la información a la fecha de entrega

| Indicador | Valor |
|---|---|
| RUN cargados | **415** |
| Período cubierto | 15-12-2025 a 08-09-2026 |
| Registros de producción | 2.843 |
| Productos en la Tabla Maestra | 336 |
| Escuadrías distintas | 21 |
| Volumen Nominal acumulado | 6.949,9 m³ |
| Piezas acumuladas | 7.465.292 |
| Cortes acumulados | 11.201.105 |
| Corridas de rechazo identificadas | 18 |

---

## 5. Últimas modificaciones

### 5.1 Corrección crítica: cambio de formato del scanner (resuelta)

**Situación.** A partir del **26 de agosto de 2026** los archivos exportados por el scanner dejaron de poder cargarse en el sistema.

**Causa.** El scanner modificó la tabla de productos del archivo: pasó de 18 a 19 columnas —se agregó `Cantidad [ % ]`— y cambió el orden de varias de ellas. El sistema validaba que el conjunto de columnas fuera exactamente el conocido, por lo que rechazaba el archivo completo.

**Solución aplicada.** El sistema ahora **identifica cada columna por su nombre** y no por su posición, y solo exige la presencia de las columnas que realmente utiliza. Las columnas nuevas o reordenadas se ignoran sin afectar la carga. Esto significa que **un futuro cambio de columnas del scanner ya no volverá a interrumpir la operación**.

**Verificación.** Se comprobó que los archivos del formato antiguo siguen produciendo resultados idénticos a los ya cargados, sin ninguna diferencia en los datos históricos.

### 5.2 Recuperación del período no cargado

Se incorporaron a la base los **32 RUN pendientes del 24-08 al 08-09**, más dos RUN antiguos del 07-08 que nunca habían ingresado. La información de agosto y septiembre quedó completa y visible en los tableros.

### 5.3 Mayor robustez del proceso de carga masiva

El proceso de carga de respaldo ahora **omite y reporta** los archivos dañados, bloqueados por Excel o temporales, y continúa con el resto. Antes, un único archivo defectuoso interrumpía toda la carga.

### 5.4 Mejoras funcionales previas incluidas en esta entrega

- Nuevo selector de períodos con accesos rápidos (últimos 7 / 30 / 90 / 120 días, este mes) y modo personalizado.
- Nuevo gráfico de **Metros Lineales en el tiempo**.
- Nuevo panel de **Total de Cortes por RUN** y su evolución.
- Etiquetas de datos sobre los gráficos, para lectura directa de los valores.
- Gráfico de escuadrías principales por volumen, en reemplazo del ranking por producto.

---

## 6. Cómo leer los indicadores

**Importante:** los indicadores del Dashboard (Volumen Nominal, Rendimiento, N° de RUN) **corresponden siempre al período seleccionado en el filtro lateral**, no al total histórico. El Dashboard abre por defecto en "Últimos 30 días".

Para analizar todo el histórico, seleccionar **"Personalizado"** en el selector de período e indicar una fecha de inicio anterior a diciembre de 2025.

---

## 7. Puntos de atención y recomendaciones

### 7.1 Tres archivos pendientes de re-exportar

Quedaron fuera de la carga por problemas en el archivo de origen, no del sistema:

| Archivo | Problema | Acción requerida |
|---|---|---|
| `RUN_2833` (07-08) | Archivo dañado, no es un Excel válido | Re-exportar desde el scanner |
| `RUN_2834` (07-08) | Archivo dañado, no es un Excel válido | Re-exportar desde el scanner |
| `RUN_2` (25-08) | Exportado sin la columna `Volumen Nominal [ m³ ]` | Re-exportar con esa columna activa |

### 7.2 Mantener la configuración de columnas del scanner

La columna **`Volumen Nominal [ m³ ]` es indispensable** para calcular el rendimiento. Si el scanner exporta sin ella, el archivo no puede cargarse. Se recomienda fijar la configuración de columnas de exportación y no modificarla.

### 7.3 Reinicio del contador de RUN del scanner

El **25 de agosto de 2026 el scanner reinició su numeración de RUN**, volviendo a empezar desde 1 (los RUN anteriores llegaban a 2.896). Hoy esto no genera conflicto, porque los números bajos estaban libres.

Sin embargo, **cuando el contador nuevo vuelva a alcanzar el rango del histórico se producirán números de RUN repetidos**, y los nuevos no podrán cargarse. Se recomienda:

1. Solicitar al proveedor del scanner que **no reinicie el contador**, o
2. Planificar un ajuste del sistema para identificar cada RUN por número **y fecha**.

### 7.4 Nomenclatura de los archivos

Se detectaron archivos cuyo nombre indica una escuadría distinta a la real (por ejemplo `20.5x140` cuando los productos son `20,5x143`). El sistema toma la escuadría de los productos, por lo que **el dato registrado es correcto**, pero conviene corregir la práctica de nombrado para evitar confusiones.

### 7.5 Cerrar los archivos antes de cargarlos

Un archivo abierto en Excel queda bloqueado y no puede leerse. Debe cerrarse antes de subirlo.

### 7.6 Mejora identificada

Si se sube un archivo dañado desde la carga web, la página muestra un mensaje técnico en lugar de un aviso claro. No impide la operación y queda identificado para corregir en una próxima iteración.

---

## 8. Conformidad

Se solicita al Área de Operaciones revisar la presente entrega y comunicar su conformidad u observaciones.

Para consultas, soporte o requerimientos de nuevos indicadores:
**patricio.sagredo@glover.cl**
