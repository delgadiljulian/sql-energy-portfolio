# Fuentes y alcance

## Fuentes oficiales activas

| ID | Contenido | Fuente primaria | Cobertura |
|---|---|---|---|
| `rrc_iwar_actual` | Pozos inactivos en los registros de prorrateo | [RRC: IWAR](https://www.rrc.texas.gov/oil-and-gas/compliance-enforcement/hb-2259hb-3134-inactive-well-requirements/inactive-well-aging-report-iwar/) | Corte indicado en el manifiesto |
| `eia_wti` | WTI spot Cushing | [EIA: RWTC](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=D) | Diaria; fechas del manifiesto |
| `eia_brent` | Brent spot Europa | [EIA: RBRTE](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=D) | Diaria; fechas del manifiesto |
| `eia_produccion_texas` | Producción de crudo de Texas | [EIA: MCRFPTX1](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=MCRFPTX1&f=M) | Mensual, miles de barriles |
| `eia_refinerias_texas` | Capacidad operable de destilación de crudo | [EIA-820](https://www.eia.gov/petroleum/refinerycapacity/) | Instalación, Texas, corte anual |

`data/fuentes_oficiales.json` es el registro operativo: guarda URL, descarga UTC, fecha de corte o período, unidad, filas y hashes del original y del CSV normalizado.

## Fuentes heredadas

- **IWAR histórico:** 102.672 registros. El mes 2020-10 se infiere de `Shut In Date + Current Inactive Years/Months` en todas las filas; no se encontró el recibo original de descarga.
- **P-5 histórico:** contiene 74.429 organizaciones, incluidas inactivas. Su fecha de corte no se conoce. Las ciudades son direcciones registradas en ese archivo, no sedes corporativas verificadas en 2026.
- **Producción por cuencas:** se generó con una fórmula para ocho condados en 2023–2024. Solo se carga en `demo_produccion_cuencas`.
- **Empresas, terminales y refinerías iniciales:** datos manuales sin referencias por fila. Permanecen archivados y no alimentan las tablas analíticas.
- **Series de precios iniciales:** permanecen archivadas; el modelo usa las descargas directas de la EIA.

Todos aparecen en `data/fuentes_heredadas.json`.

## Reglas de interpretación

1. IWAR significa pozos inactivos; no representa el inventario total de pozos ni la producción de un operador.
2. El campo de RRC es un campo petrolero o gasífero, no necesariamente una formación geológica.
3. La fecha de registro original es la fecha más antigua del pozo que consta en la RRC; no se presenta como fecha de inicio de producción.
4. El costo IWAR es una estimación regulatoria de taponamiento basada en la metodología de la RRC. No se interpreta como pasivo contable.
5. `Well Plugged=Y` informa que la oficina recibió el Form W-3, aunque el registro todavía aparece en el IWAR.
6. La capacidad EIA-820 es capacidad operable de barriles por día calendario, no producción o utilización efectiva.
7. Los promedios mensuales de precios usan únicamente observaciones disponibles. El spread diario existe solo cuando WTI y Brent están presentes.
8. El último período puede estar incompleto; las consultas muestran conteos o excluyen años parciales.
9. Una asociación temporal entre precios y producción es descriptiva y no demuestra causalidad.
10. Las localidades usadas como “entorno industrial de Houston” son una selección explícita en la consulta, no una delimitación oficial del área metropolitana.
