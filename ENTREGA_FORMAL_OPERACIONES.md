# Entrega formal del proyecto Scanner Maderera

**Dirigido a:** Área de Operaciones  
**Fecha de emisión:** 9 de septiembre de 2026  
**Proyecto:** Scanner Maderera — gestión y análisis de producción  
**Versión de referencia:** `3eecd99` del 9 de septiembre de 2026  
**Asunto:** Entrega del proyecto, beneficios operacionales y últimas modificaciones

## 1. Presentación de la entrega

Por medio del presente documento se formaliza la entrega documental del proyecto **Scanner Maderera** al Área de Operaciones. La solución permite centralizar los archivos de producción exportados por el scanner, procesar su información y consultar indicadores que apoyan el seguimiento de la producción y del rendimiento nominal.

El proyecto integra la carga de archivos RUN en formato Excel, la clasificación automática de productos, la consulta de antecedentes de cada corrida y la visualización de resultados por período, escuadría, turno y operador, según las opciones disponibles en cada módulo.

La entrega comprende las funcionalidades implementadas en la versión de referencia y las modificaciones descritas en este documento. La recepción conforme y los responsables de continuidad operacional se registran al final.

## 2. Alcance funcional entregado

| Módulo | Funcionalidades disponibles | Utilidad para Operaciones |
| --- | --- | --- |
| **Dashboard / Informe Scanner** | Volumen nominal, rendimiento nominal y número de RUNs; evolución de volumen, metros lineales, rendimiento y cortes; distribución por tipo y asignación; escuadrías con mayor volumen; producción y rendimiento por operador; destino de recuperación y RUNs recientes. | Reunir en una misma vista los principales antecedentes de producción y facilitar la identificación de cambios en el comportamiento del proceso. |
| **Rendimiento Mensual** | Consulta del período seleccionado, rendimiento total y por los tres turnos, participación de Blank y CTK, desglose por asignación y evolución diaria. | Apoyar reuniones de seguimiento y cierres de período con criterios de cálculo consistentes. |
| **Índice de Rendimiento** | Comparación del rendimiento del período con el promedio histórico disponible para la escuadría seleccionada; visualización diaria, semanal o mensual. | Contar con una referencia histórica para detectar desviaciones y orientar revisiones operacionales. |
| **Cargar RUN** | Carga de uno o varios archivos `.xlsx`, validaciones, vista previa, clasificación automática, confirmación de carga y recarga explícita de RUNs existentes. | Simplificar la incorporación de información y revisar los datos antes de almacenarlos. |
| **Tabla Maestra de Asignación** | Consulta y edición de la clasificación de productos, incluyendo escuadría, tipo, asignación y destino de recuperación. | Facilitar la revisión de los criterios utilizados para organizar la producción. |
| **Historial de Cargas** | Consulta de hasta 500 registros recientes, con los antecedentes almacenados de cada RUN. | Facilitar la comprobación de cargas y el seguimiento de sus archivos de origen. |

El gráfico de cortes depende de la disponibilidad del campo correspondiente en la base de datos. Las vistas por operador y destino de recuperación dependen de que esa información esté presente en los registros.

## 3. Beneficios para el Área de Operaciones

1. **Centralización de la información.** Consolida los datos de los archivos RUN en una base de datos común, facilitando la consulta de antecedentes y la revisión de distintos períodos.
2. **Menor trabajo manual de preparación.** La carga múltiple y la clasificación automática reducen la necesidad de transcribir datos y completar categorías producto por producto.
3. **Clasificación consistente.** Aplica reglas compartidas para identificar escuadría, tipo, producto principal, coproductos y recuperación a partir del contenido de cada corrida.
4. **Mayor control de calidad en la carga.** Detecta columnas necesarias ausentes, RUNs ya registrados y archivos sin productos válidos; además, advierte diferencias entre la escuadría del nombre de archivo y la calculada desde los productos.
5. **Prevención de duplicaciones accidentales.** Verifica la existencia previa del número de RUN y solicita una confirmación específica para reemplazar sus datos.
6. **Trazabilidad de la producción.** Conserva el número de RUN, archivo de origen, fecha, turno, operador, horarios y totales, junto con el detalle de producción asociado.
7. **Seguimiento de tendencias.** Permite observar la evolución de volumen, metros lineales, cortes y rendimiento para localizar períodos que requieran revisión.
8. **Análisis por escuadría, turno y operador.** Facilita comparaciones operacionales y la búsqueda de oportunidades de mejora, considerando las condiciones de producción de cada caso.
9. **Visibilidad del aprovechamiento y la recuperación.** Muestra la distribución entre productos principales, coproductos y recuperación, así como los destinos de esta última cuando están informados.
10. **Referencia histórica para la gestión.** Compara el rendimiento del período con los datos históricos disponibles y entrega contexto para evaluar desviaciones.
11. **Consulta más ágil.** Incorpora filtros por fechas, períodos predefinidos, agrupaciones temporales y actualización manual de las vistas.
12. **Mayor continuidad frente a cambios de exportación.** La última modificación admite variaciones en el orden y la cantidad de columnas de los archivos, siempre que se mantengan los campos obligatorios y la estructura prevista.
13. **Mejor manejo de incidencias en la carga inicial masiva.** El script de carga omite archivos temporales de Excel y continúa con los demás archivos cuando se produce un error al abrir o interpretar uno de ellos.
14. **Base para decisiones y seguimiento de mejoras.** La información consolidada permite respaldar reuniones operacionales, priorizar revisiones y comparar resultados posteriores a una intervención.

Estos beneficios describen las capacidades de la solución y su utilidad esperada. No se asignan porcentajes de ahorro, aumentos de productividad ni reducciones de costos, dado que esta entrega no incluye una medición de impacto en operación.

## 4. Última modificación incorporada

**Fecha:** 9 de septiembre de 2026.  
**Referencia:** `3eecd99` — “Ajuste en la seleccion de columnas, por cambio en su orden”.

### Motivo del ajuste

Los archivos exportados por el scanner presentan variaciones en el orden y la cantidad de columnas de la tabla de productos. El cambio documentado en el código considera exportaciones que, desde el 26 de agosto de 2026, incorporan la columna adicional `Cantidad [ % ]`, pasando de 18 a 19 columnas.

La versión anterior ya identificaba columnas por nombre, pero exigía un conjunto fijo de 18 encabezados. Esa exigencia podía impedir la carga de archivos con columnas adicionales o con diferencias en campos que el sistema no utiliza.

### Cambios realizados y efecto operacional

| Cambio | Efecto para Operaciones |
| --- | --- |
| Lectura dinámica de encabezados e identificación por nombre. | Permite procesar columnas reordenadas y adicionales dentro de la estructura admitida. |
| Validación centrada en las 12 columnas realmente utilizadas. | Evita rechazos por ausencia o incorporación de columnas accesorias. |
| Normalización de espacios y saltos de línea en los encabezados. | Reduce errores de reconocimiento debidos a diferencias de presentación del Excel. |
| Mensajes que detallan las columnas obligatorias faltantes y las encontradas. | Facilita identificar la configuración que debe revisarse en la exportación. |
| Exclusión de archivos temporales `~$...` en el script de carga inicial. | Evita intentar procesar archivos auxiliares generados por Excel. |
| Continuación de la carga inicial ante errores de apertura o interpretación de un archivo. | Permite avanzar con los archivos restantes y dejar identificado el archivo con error. |

**Archivos modificados:** `scanner_app/config.py`, `scanner_app/parsing/run_file.py` y `scripts/seed_inicial.py`.

La lectura de encabezados comienza en la ubicación prevista de la tabla, termina en la primera celda vacía y tiene un máximo de 40 columnas. El ajuste no implica compatibilidad con cualquier formato de Excel. Las mejoras de exclusión de temporales y continuidad ante errores corresponden al script de carga inicial masiva.

## 5. Otras modificaciones recientes relevantes

| Fecha | Modificación | Aporte operacional |
| --- | --- | --- |
| 18-08-2026 | Incorporación del módulo Índice de Rendimiento (`d44a204`). | Comparación del rendimiento real del período con la referencia histórica. |
| 17-08-2026 | Mejora del selector de fechas, incorporación del gráfico de metros lineales y etiquetas de datos (`12b67c6`). | Selección de períodos más cómoda y lectura directa de los valores graficados. |
| 17-08-2026 | Registro de total de cortes por RUN y gráfico de evolución (`b49d32d`), junto con una protección del panel ante bases sin el campo correspondiente (`0cab082`). | Seguimiento de cortes y visualización condicionada a la disponibilidad del dato. |
| 14-08-2026 | Ajustes de diseño de la aplicación (`a740ee6`). | Mejora de la presentación de las pantallas. |
| 12-08-2026 | Corrección del gráfico de rendimiento y presentación de fechas en español (`d80e832`); agrupación del gráfico de mayor volumen por escuadría (`579aa37`). | Facilita la interpretación de tendencias y la comparación de escuadrías. |

## 6. Criterios para el uso e interpretación

- **Origen de los datos:** el número de RUN, la fecha y el turno se obtienen de la información interna del archivo. El nombre del archivo aporta señales de escuadría y rechazo.
- **Filas consideradas:** se excluyen los productos con cantidad y/o volumen nominal cero, conforme a las reglas de carga.
- **Rendimiento nominal:** el cálculo implementado promedia, entre RUNs, la suma de sus porcentajes de volumen nominal incluidos. Cada RUN se considera una unidad independiente; este indicador debe interpretarse según esa metodología.
- **Blank y CTK:** sus indicadores representan la participación de cada tipo en el volumen nominal total del período.
- **Rendimiento Meta:** corresponde al promedio histórico disponible para los filtros aplicables, incluida la selección de escuadría y la inclusión o exclusión de rechazo. Es una referencia calculada que puede cambiar al incorporarse datos; no es una meta presupuestaria ingresada manualmente.
- **Comparaciones entre pantallas:** deben utilizarse períodos y criterios de rechazo equivalentes. El Dashboard incluye rechazo por defecto, mientras que Rendimiento Mensual e Índice de Rendimiento lo excluyen por defecto.
- **Ediciones de la tabla maestra:** son ajustes temporales; la clasificación de un producto se recalcula cuando vuelve a aparecer en una nueva carga.
- **Recarga de un RUN:** reemplaza sus datos de producción existentes y debe utilizarse cuando corresponda corregir la carga.

## 7. Continuidad operacional y recepción

Para el uso cotidiano, Operaciones debe exportar los archivos RUN del scanner, cargarlos desde **Cargar RUN**, revisar la vista previa y los mensajes, confirmar la carga y comprobar su registro en el historial. Posteriormente puede consultar los indicadores con los filtros del período de interés.

La aplicación está desarrollada en Python con Streamlit y utiliza una conexión PostgreSQL. Su continuidad requiere disponer de la aplicación ejecutable, la base de datos con la estructura requerida y la configuración de conexión correspondiente.

Para completar la recepción, se propone registrar:

- La dirección de acceso y el ambiente de operación.
- El responsable de cargar y revisar la información en Operaciones.
- El responsable técnico y el canal de soporte.
- El responsable y la periodicidad de los respaldos de la base de datos.
- La verificación conjunta de una carga representativa, su historial y sus indicadores.

**Base de esta entrega:** revisión del código fuente y del historial Git de la versión indicada. La elaboración de este documento no incluye una prueba de conexión a la base de datos ni una validación del ambiente productivo.

## 8. Constancia de entrega y recepción

Se presenta al Área de Operaciones el proyecto Scanner Maderera con el alcance funcional, los beneficios y las modificaciones descritos, para su recepción y utilización como herramienta de apoyo al control de producción.

| Antecedente | Registro |
| --- | --- |
| Responsable de la entrega | Por completar |
| Responsable de recepción — Operaciones | Por completar |
| Responsable de soporte técnico | Por completar |
| Dirección de acceso / ambiente | Por completar |
| Fecha efectiva de recepción | Por completar |
| Resultado de la validación operacional | Por completar |
| Observaciones o compromisos pendientes | Por completar |
| Conformidad de quien entrega | Por completar |
| Conformidad de quien recibe | Por completar |
