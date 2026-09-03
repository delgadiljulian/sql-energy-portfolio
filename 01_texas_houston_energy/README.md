# SQL aplicado a la energía de Texas y Houston

Proyecto de aprendizaje y portafolio con SQLite. Separa datos oficiales observados, archivos heredados, información manual no verificada y una muestra simulada.

## Qué puede responder

- Evolución de la producción mensual total de crudo de Texas (EIA).
- Precios diarios WTI y Brent y su diferencial (EIA).
- Capacidad operable de refinación por instalación y distrito de refinación en Texas (EIA-820).
- Pozos inactivos del IWAR por corte, condado y operador (RRC).
- Ejercicios didácticos con datos simulados, siempre identificados como tales.

No permite medir producción por cuenca o empresa, utilización efectiva de refinerías, ni afirmar sedes corporativas actuales. El IWAR contiene pozos **inactivos**, no todos los pozos de Texas.

## Inicio rápido

Desde esta carpeta:

```powershell
python ejecutar.py
python ejecutar.py consultas/03_pozos_inactivos_actuales.sql
python ejecutar.py --todas --limite 15
python ejecutar.py consultas/05_produccion_observada.sql --csv outputs/exportaciones
```

El ejecutor abre `data/houston_energy_v2.db` en modo lectura. Una consulta que intente cambiarla falla, salvo que se use deliberadamente `--escritura`.

## Reconstrucción reproducible

Las fuentes ya descargadas se verifican por SHA-256 antes de cada carga. La base se construye en un archivo temporal, pasa controles y solo entonces sustituye la versión anterior:

```powershell
python preparar.py
python scripts/validar_base.py
python -m unittest discover -s tests -v
```

Para actualizar los archivos oficiales:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe preparar.py --actualizar
```

Cada actualización crea un lote inmutable. Si falla una descarga, conversión o validación, el manifiesto y la base anteriores se conservan.

## Estructura

- `consultas/`: guías SQL ordenadas y área de práctica.
- `data/fuentes_oficiales.json`: procedencia, fechas, unidades, hashes y conteos oficiales.
- `data/fuentes_heredadas.json`: inventario y limitaciones de los archivos iniciales.
- `data/raw/oficiales/`: archivos oficiales y sus versiones normalizadas.
- `sql/esquema.sql`: modelo, restricciones, índices y vistas.
- `scripts/descargar_fuentes.py`: descarga y conversión.
- `scripts/construir_base.py`: carga atómica y controles.
- `scripts/validar_base.py`: validación independiente en lectura.
- `outputs/VALIDACION.md`: último resultado legible de los controles.
- `docs/`: fuentes, diccionario y decisiones metodológicas.
- `data/backups/`: copias locales ignoradas por control de versiones.

## Ruta de aprendizaje

1. `01_primeras_consultas.sql`: filtros y orden.
2. `02_metricas_houston.sql`: agregaciones y funciones de ventana.
3. `03_pozos_inactivos_actuales.sql`: granularidad, deduplicación y datos regulatorios.
4. `04_precios_y_ventanas.sql`: series temporales, `LAG` y medias móviles.
5. `05_produccion_observada.sql`: conversiones, comparaciones anuales y joins temporales.
6. `06_ejercicio_datos_simulados.sql`: práctica claramente separada de la evidencia observada.
7. `bitacora_consultas_completas.sql`: consultas de la sesión con alcance, denominadores y lenguaje corregidos.

Consulta [FUENTES.md](docs/FUENTES.md) y [DICCIONARIO_DATOS.md](docs/DICCIONARIO_DATOS.md) antes de interpretar resultados.

## Base inicial conservada

`data/houston_energy.db` es la base inicial. Estaba abierta durante este fortalecimiento y Windows no permitió renombrarla; los comandos del proyecto usan únicamente `houston_energy_v2.db`. El respaldo integral anterior a los cambios permanece en `data/backups/`.
