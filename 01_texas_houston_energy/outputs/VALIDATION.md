# Validación de la base

Carga: 07f9c9c9-3084-4a3c-96fe-563b3153f8d6
UTC: 2026-09-03T16:57:44.078068+00:00

Controles obligatorios aprobados: 29.

## Registros y API por corte

| Fuente | Registros conservados | API distintos | API con varios operadores |
|---|---:|---:|---:|
| rrc_iwar_actual | 121221 | 117169 | 155 |
| rrc_iwar_historico | 102672 | 99198 | 132 |

Las filas repetidas por API se conservan. La vista por API deja en NULL los atributos contradictorios.
El corte heredado 2020-10 es inferido. El corte oficial actual consta en fuentes_oficiales.json.
El P-5 heredado no certifica sedes ni estados actuales.

## Incidencias de normalización

| Fuente | Campo | Motivo | Filas |
|---|---|---|---:|
| rrc_iwar_actual | API Depth | Profundidad no positiva; se conserva NULL | 169 |
| rrc_iwar_actual | Original Completion Date | Fecha inválida; se conserva NULL | 1372 |
| rrc_iwar_actual | Original Completion Date | Fecha no informada; se conserva NULL | 77 |
| rrc_iwar_historico | API Depth | Profundidad no positiva; se conserva NULL | 181 |
| rrc_iwar_historico | Original Completion Date | Fecha inválida; se conserva NULL | 1449 |
| rrc_iwar_historico | Original Completion Date | Fecha no informada; se conserva NULL | 65 |
| rrc_p5_historico | Last P5 Filed Date | Fecha no informada; se conserva NULL | 13115 |

Los originales permanecen intactos; cada incidencia apunta a su fuente y fila.
No se sustituyen números ausentes por cero. Los precios negativos observados se conservan.

Detalle reproducible: validacion.json y consultas/00_calidad_datos.sql.
