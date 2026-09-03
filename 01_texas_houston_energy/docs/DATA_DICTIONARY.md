# Diccionario de datos

Base: `data/houston_energy_v2.db`. La unidad de observación figura en cada tabla.

## Metadatos

### `fuentes` — una fila por conjunto de datos

`fuente_id` identifica la fuente; `naturaleza` distingue `observado_oficial`, `observado_heredado`, `simulado` y `manual_no_verificado`; `uso` indica si participa en análisis, ejercicios o solo archivo. Incluye fecha de corte, período, unidad, ruta, SHA-256, filas y metadata completa en JSON.

### `ejecucion_carga` — una fila por base publicada

Registra UUID, hora UTC, versión de SQLite, versión del modelo y huella del código de carga.

### `incidencias_carga` — una fila por normalización no fatal

Conserva fuente, fila, campo, valor original y motivo. Por ejemplo, fechas cero o profundidades no positivas convertidas a `NULL`.

## Railroad Commission of Texas

### `operadores` — una fila por número RRC

Contiene únicamente `operador_id`, de seis dígitos. Es la dimensión estable usada por las claves foráneas.

### `operadores_p5_historico` — una fila por organización del archivo heredado

Nombre, estado P-5, forma jurídica, dirección registrada, garantía financiera y última presentación disponibles en el archivo original. Son datos históricos de fecha desconocida.

### `pozos_inactivos_registros` — una fila por fila del IWAR y corte

| Columna | Significado |
|---|---|
| `fuente_id`, `fila_origen` | Linaje completo; juntos son únicos. |
| `api` | Identificador de 10 dígitos: estado 42 + condado + número único. |
| `api_original` | Valor combinado presente únicamente en el archivo heredado. |
| `operador_id`, `operador_nombre` | Operador de registro en ese corte. |
| `condado`, `distrito_rrc` | Geografía administrativa; el distrito es texto para conservar `6E`, `7B`, `7C` y `8A`. |
| `tipo_recurso` | Petróleo, gas o mixto según O/G Code. |
| Números y nombres de arrendamiento, pozo y campo | Identificadores del registro RRC, conservados como texto. |
| `profundidad_pies` | API Depth; valores cero quedan `NULL` con incidencia. |
| `fecha_registro_original` | Fecha más antigua que consta para el pozo. |
| `mes_cierre` | Primer mes de inactividad registrado. |
| `meses_inactivo` | Años por 12 más meses del IWAR. |
| `mes_corte_inferido` | Mes calculado para validar la coherencia temporal. |
| `costo_taponamiento_estimado_usd` | Cost Calculation de la RRC. Cero se conserva como cero. |
| `taponamiento_reportado` | Indicador Well Plugged. |
| `es_pozo_huerfano` | Disponible solo en el histórico; `NULL` en el archivo oficial actual. |
| `estado_extension` | Estado de la extensión de taponamiento cuando existe. |

### `pozos_inactivos` y `vw_pozos_inactivos` — una fila por `fuente_id + api`

La tabla materializa la consolidación para acelerar las consultas y la vista mantiene una interfaz legible. Conservan el número de filas del API. Un atributo común se asigna solo cuando no hay contradicción. Exponen `n_operadores`, `n_distritos` y `n_campos`; los atributos contradictorios quedan `NULL`.

### `vw_conflictos_api`

Subconjunto anterior con más de un operador, distrito o campo. Sirve para auditar cambios regulatorios, registros múltiples o granularidad.

## EIA

### `precios_observaciones` — referencia y fecha

Precio WTI o Brent en USD/barril. Los faltantes son `NULL`; los precios negativos observados son válidos.

### `precios_crudo_diario` — una fila por fecha

Vista con WTI, Brent y `spread_brent_wti = Brent - WTI`. El spread es `NULL` si falta una referencia.

### `produccion_texas_mensual` — una fila por mes

Producción EIA MCRFPTX1 en miles de barriles para todo Texas.

### `vw_produccion_texas_mensual`

Añade barriles mensuales, días del mes y barriles/día promedio calculado con el denominador calendario correcto.

### `refinerias_texas` — instalación y fecha de corte

Corporación, operador, localidad, distrito de refinación, PADD y capacidad operable de destilación atmosférica de crudo en barriles/día calendario.

## Ejercicio

### `demo_produccion_cuencas` — cuenca, condado, año y mes

Muestra generada por fórmula. `naturaleza='simulado'` está protegida por una restricción y su fuente también debe tener naturaleza simulada.
