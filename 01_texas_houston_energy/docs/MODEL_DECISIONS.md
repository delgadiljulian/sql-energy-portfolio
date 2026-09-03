# Decisiones metodológicas

## Granularidad IWAR

El API se repetía en 3.138 grupos del corte heredado y las filas no eran duplicados exactos. Se conservan todas en `pozos_inactivos_registros`. `vw_pozos_inactivos` consolida por corte y API sin seleccionar arbitrariamente la primera fila; `vw_conflictos_api` muestra las contradicciones.

## Identificadores y ausencias

- API y operador se guardan como texto de ancho fijo para conservar ceros iniciales.
- El distrito RRC se guarda como texto y se normaliza a dos dígitos cuando es numérico.
- Valores ausentes se convierten a `NULL`; un cero informado permanece cero.
- Fechas inválidas y profundidades no positivas producen incidencias trazables.
- No se infiere que un pozo sea huérfano cuando el archivo actual carece del campo.

## Publicación segura

La reconstrucción valida hashes antes de crear una base temporal. Comprueba integridad, claves foráneas, conteos por fuente, meses de corte IWAR, continuidad mensual de producción y separación de datos simulados. También detecta cambios concurrentes en la base. Solo publica después de superar los controles y crea un respaldo de la versión anterior.

## Actualizaciones

Cada descarga nueva queda en un directorio inmutable con sus archivos y recibo. `fuentes_oficiales.json` cambia únicamente después de convertir y validar todo el lote. Las fuentes heredadas no se sobrescriben.
