PRAGMA foreign_keys = ON;
PRAGMA user_version = 2;

CREATE TABLE fuentes (
    fuente_id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    naturaleza TEXT NOT NULL CHECK(naturaleza IN ('observado_oficial','observado_heredado','simulado','manual_no_verificado')),
    uso TEXT NOT NULL CHECK(uso IN ('analitico','didactico','archivo')),
    fecha_corte TEXT,
    periodo_inicio TEXT,
    periodo_fin TEXT,
    unidad TEXT NOT NULL,
    archivo TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK(length(sha256)=64),
    filas_origen INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE operadores (
    operador_id TEXT PRIMARY KEY CHECK(length(operador_id)=6 AND operador_id NOT GLOB '*[^0-9]*')
);

-- P-5 heredado: ni su dirección ni su estado se afirman vigentes en 2026.
CREATE TABLE operadores_p5_historico (
    operador_id TEXT PRIMARY KEY REFERENCES operadores(operador_id),
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    nombre TEXT NOT NULL,
    estado_p5 TEXT,
    tipo_organizacion TEXT,
    ciudad TEXT,
    estado TEXT,
    codigo_postal TEXT,
    garantia_financiera_usd REAL CHECK(garantia_financiera_usd>=0),
    opcion_garantia TEXT,
    tipo_garantia TEXT,
    ultima_presentacion TEXT
);
CREATE INDEX idx_p5_ciudad ON operadores_p5_historico(ciudad,estado);

CREATE TABLE pozos_inactivos_registros (
    registro_id INTEGER PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    fila_origen INTEGER NOT NULL,
    api TEXT NOT NULL CHECK(length(api)=10 AND substr(api,1,2)='42' AND api NOT GLOB '*[^0-9]*'),
    api_original TEXT,
    operador_id TEXT NOT NULL REFERENCES operadores(operador_id),
    operador_nombre TEXT NOT NULL,
    condado TEXT NOT NULL,
    distrito_rrc TEXT NOT NULL CHECK(distrito_rrc IN ('01','02','03','04','05','06','6E','7B','7C','08','8A','09','10')),
    tipo_recurso TEXT NOT NULL CHECK(tipo_recurso IN ('Petróleo','Gas','Mixto')),
    numero_arrendamiento TEXT,
    numero_pozo TEXT,
    unidad_petrolera TEXT,
    nombre_arrendamiento TEXT,
    numero_campo TEXT,
    nombre_campo TEXT,
    profundidad_pies INTEGER CHECK(profundidad_pies>0),
    fecha_registro_original TEXT,
    mes_cierre TEXT,
    meses_inactivo INTEGER CHECK(meses_inactivo>=0),
    mes_corte_inferido TEXT,
    costo_taponamiento_estimado_usd REAL CHECK(costo_taponamiento_estimado_usd>=0),
    taponamiento_reportado INTEGER CHECK(taponamiento_reportado IN (0,1)),
    es_pozo_huerfano INTEGER CHECK(es_pozo_huerfano IN (0,1)),
    estado_extension TEXT,
    UNIQUE(fuente_id,fila_origen)
);
CREATE INDEX idx_registros_api ON pozos_inactivos_registros(fuente_id,api);
CREATE INDEX idx_registros_operador ON pozos_inactivos_registros(operador_id);
CREATE INDEX idx_registros_condado ON pozos_inactivos_registros(fuente_id,condado);

-- Una fila materializada por API y fuente; evita recalcular 223 mil registros en cada consulta.
CREATE TABLE pozos_inactivos (
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    api TEXT NOT NULL,
    registros_por_api INTEGER NOT NULL CHECK(registros_por_api>=1),
    n_operadores INTEGER NOT NULL CHECK(n_operadores>=1),
    operador_id TEXT REFERENCES operadores(operador_id),
    operador_nombre TEXT,
    condado TEXT,
    n_distritos INTEGER NOT NULL CHECK(n_distritos>=1),
    distrito_rrc TEXT,
    tipo_recurso TEXT NOT NULL CHECK(tipo_recurso IN ('Petróleo','Gas','Mixto')),
    n_campos INTEGER NOT NULL CHECK(n_campos>=0),
    profundidad_pies INTEGER,
    meses_inactivo INTEGER,
    costo_taponamiento_estimado_usd REAL,
    taponamiento_reportado INTEGER,
    es_pozo_huerfano INTEGER,
    PRIMARY KEY(fuente_id,api)
);
CREATE INDEX idx_pozos_inactivos_condado ON pozos_inactivos(fuente_id,condado,tipo_recurso);
CREATE INDEX idx_pozos_inactivos_operador ON pozos_inactivos(fuente_id,operador_id);
CREATE VIEW vw_pozos_inactivos AS SELECT * FROM pozos_inactivos;

CREATE VIEW vw_conflictos_api AS
SELECT * FROM vw_pozos_inactivos WHERE n_operadores>1 OR n_distritos>1 OR n_campos>1;

CREATE TABLE precios_observaciones (
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    referencia TEXT NOT NULL CHECK(referencia IN ('WTI','BRENT')),
    fecha TEXT NOT NULL,
    precio_usd_barril REAL,
    PRIMARY KEY(referencia,fecha)
);
-- Los precios negativos observados son válidos; las ausencias permanecen NULL.
CREATE VIEW precios_crudo_diario AS
WITH p AS (
    SELECT fecha,
           MAX(CASE WHEN referencia='WTI' THEN precio_usd_barril END) AS precio_wti_usd,
           MAX(CASE WHEN referencia='BRENT' THEN precio_usd_barril END) AS precio_brent_usd
    FROM precios_observaciones GROUP BY fecha
)
SELECT *,ROUND(precio_brent_usd-precio_wti_usd,2) AS spread_brent_wti FROM p;

CREATE TABLE produccion_texas_mensual (
    fecha TEXT PRIMARY KEY CHECK(substr(fecha,9,2)='01'),
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    miles_barriles INTEGER NOT NULL CHECK(miles_barriles>=0)
);
CREATE VIEW vw_produccion_texas_mensual AS
SELECT fecha,fuente_id,miles_barriles,miles_barriles*1000 AS barriles_crudo_mes,
       CAST(strftime('%d',date(fecha,'+1 month','-1 day')) AS INTEGER) AS dias_mes,
       ROUND(1000.0*miles_barriles/CAST(strftime('%d',date(fecha,'+1 month','-1 day')) AS INTEGER),2) AS barriles_dia_promedio
FROM produccion_texas_mensual;

CREATE TABLE refinerias_texas (
    refineria_id INTEGER PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    fecha_corte TEXT NOT NULL,
    corporacion TEXT NOT NULL,
    operador TEXT NOT NULL,
    localidad TEXT NOT NULL,
    distrito_refinacion TEXT NOT NULL,
    padd TEXT NOT NULL,
    capacidad_barriles_dia_calendario INTEGER NOT NULL CHECK(capacidad_barriles_dia_calendario>=0),
    UNIQUE(fecha_corte,operador,localidad)
);

CREATE TABLE demo_produccion_cuencas (
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    naturaleza TEXT NOT NULL DEFAULT 'simulado' CHECK(naturaleza='simulado'),
    cuenca TEXT NOT NULL,
    condado TEXT NOT NULL,
    region TEXT NOT NULL,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
    barriles_crudo_mes INTEGER NOT NULL CHECK(barriles_crudo_mes>=0),
    mcf_gas_mes INTEGER NOT NULL CHECK(mcf_gas_mes>=0),
    pozos_productivos INTEGER NOT NULL CHECK(pozos_productivos>=0),
    PRIMARY KEY(cuenca,condado,anio,mes)
);

CREATE TABLE incidencias_carga (
    incidencia_id INTEGER PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuentes(fuente_id),
    fila_origen INTEGER NOT NULL,
    campo TEXT NOT NULL,
    valor_original TEXT,
    motivo TEXT NOT NULL
);
CREATE TABLE ejecucion_carga (
    carga_id TEXT PRIMARY KEY,
    iniciado_utc TEXT NOT NULL,
    sqlite_version TEXT NOT NULL,
    version_modelo INTEGER NOT NULL,
    huella_codigo TEXT NOT NULL,
    estado TEXT NOT NULL CHECK(estado='validado')
);
