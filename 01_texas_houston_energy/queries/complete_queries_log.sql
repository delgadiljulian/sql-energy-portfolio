-- ====================================================================
-- SQL ENERGY ANALYTICS: TEXAS & HOUSTON COMPREHENSIVE QUERY LOG
-- Database: data/houston_energy.db (216,000+ validated records)
-- Coverage: Upstream wells, downstream refining, market prices & production
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Wells by County and Resource Type (Volume and Depth Distribution)
-- Concepts: COUNT, AVG, MAX, GROUP BY, ORDER BY, LIMIT
-- Business insight: Identifies major producing counties in Texas.
-- --------------------------------------------------------------------
SELECT 
    condado, 
    tipo_recurso, 
    COUNT(*) AS total_pozos,
    ROUND(AVG(profundidad_pies), 0) AS profundidad_media_pies,
    MAX(profundidad_pies) AS pozo_mas_profundo
FROM pozos_texas
WHERE profundidad_pies > 0
GROUP BY condado, tipo_recurso
ORDER BY total_pozos DESC
LIMIT 15;


-- --------------------------------------------------------------------
-- 2. Deep Gas Analysis and Outlier Detection
-- Concepts: WHERE with multiple logical conditions (AND)
-- Business insight: Detects deep exploratory single-well anomalies.
-- --------------------------------------------------------------------
SELECT 
    condado,
    tipo_recurso,
    COUNT(*) AS total_pozos,
    ROUND(AVG(profundidad_pies), 0) AS profundidad_media_pies,
    MAX(profundidad_pies) AS pozo_mas_profundo
FROM pozos_texas
WHERE tipo_recurso = 'Gas' 
  AND profundidad_pies > 0
GROUP BY condado, tipo_recurso
ORDER BY profundidad_media_pies DESC
LIMIT 15;


-- --------------------------------------------------------------------
-- 3. Statistical Significance with HAVING: True Gas Basins
-- Concepts: HAVING to filter aggregated metrics after GROUP BY
-- Business insight: Robertson County leads deep gas production (14,428 ft average).
-- --------------------------------------------------------------------
SELECT 
    condado,
    tipo_recurso,
    COUNT(*) AS total_pozos,
    ROUND(AVG(profundidad_pies), 0) AS profundidad_media_pies,
    MAX(profundidad_pies) AS pozo_mas_profundo
FROM pozos_texas
WHERE tipo_recurso = 'Gas' 
  AND profundidad_pies > 0
GROUP BY condado, tipo_recurso
HAVING total_pozos >= 10
ORDER BY profundidad_media_pies DESC
LIMIT 15;


-- --------------------------------------------------------------------
-- 4. Entity Relational Join: Major Operators Headquartered in Houston
-- Concepts: INNER JOIN, table aliases (o, p), primary/foreign keys
-- Business insight: Apache leads oil well counts, while Hilcorp dominates gas.
-- --------------------------------------------------------------------
SELECT 
    o.ciudad,
    o.nombre AS empresa,
    p.tipo_recurso,
    COUNT(p.api) AS cantidad_pozos,
    ROUND(AVG(p.profundidad_pies), 0) AS prof_promedio
FROM operadores_texas o
INNER JOIN pozos_texas p ON o.operador_id = p.operador_id
WHERE o.ciudad = 'HOUSTON'
GROUP BY o.nombre, p.tipo_recurso
HAVING cantidad_pozos >= 50
ORDER BY cantidad_pozos DESC
LIMIT 12;


-- --------------------------------------------------------------------
-- 5. Economic Time Series: Historical Crude Benchmarks (1986 - Present)
-- Concepts: String parsing SUBSTR(), MIN, MAX, annual aggregations
-- Business insight: Tracks commodity super-cycles and the 2020 negative price anomaly.
-- --------------------------------------------------------------------
SELECT 
    SUBSTR(fecha, 1, 4) AS anio,
    COUNT(*) AS dias_cotizados,
    ROUND(AVG(precio_wti_usd), 2) AS precio_promedio,
    ROUND(MIN(precio_wti_usd), 2) AS precio_minimo,
    ROUND(MAX(precio_wti_usd), 2) AS precio_maximo,
    ROUND(AVG(spread_brent_wti), 2) AS spread_promedio
FROM precios_crudo_diario
WHERE precio_wti_usd IS NOT NULL
GROUP BY anio
ORDER BY anio DESC;


-- --------------------------------------------------------------------
-- 6. Technical Categorization with CASE WHEN: Depth & P&A Remediation
-- Concepts: CASE WHEN, subquery for dynamic market share calculation
-- Business insight: Deep unconventional wells cost 7x more to plug and abandon.
-- --------------------------------------------------------------------
SELECT 
    CASE 
        WHEN profundidad_pies < 3000 THEN '1. Somero / Convencional (< 3,000 ft)'
        WHEN profundidad_pies BETWEEN 3000 AND 9000 THEN '2. Profundidad Media (3,000 - 9,000 ft)'
        WHEN profundidad_pies > 9000 THEN '3. Ultra-Profundo / Fracking (> 9,000 ft)'
        ELSE '4. Sin dato registrado'
    END AS segmento_tecnico,
    COUNT(*) AS total_pozos,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pozos_texas), 1) AS porcentaje_total,
    ROUND(AVG(profundidad_pies), 0) AS prof_promedio_pies,
    ROUND(AVG(costo_abandono_estimado_usd), 0) AS costo_abandono_promedio_usd
FROM pozos_texas
WHERE profundidad_pies > 0
GROUP BY segmento_tecnico
ORDER BY segmento_tecnico ASC;


-- --------------------------------------------------------------------
-- 7. Common Table Expressions (WITH): Orphan Wells Liability Ranking
-- Concepts: WITH ... AS (CTEs for modular multistep analytics), unit conversion
-- Business insight: Quantifies state environmental exposure by county in Millions USD.
-- --------------------------------------------------------------------
WITH resumen_huerfanos AS (
    SELECT 
        condado,
        COUNT(*) AS pozos_abandonados,
        SUM(costo_abandono_estimado_usd) AS pasivo_total_usd,
        ROUND(AVG(costo_abandono_estimado_usd), 0) AS costo_promedio_pozo,
        ROUND(AVG(profundidad_pies), 0) AS prof_promedio
    FROM pozos_texas
    WHERE es_pozo_huerfano = 1
    GROUP BY condado
)
SELECT 
    condado,
    pozos_abandonados,
    ROUND(pasivo_total_usd / 1000000.0, 2) AS pasivo_total_millones_usd,
    costo_promedio_pozo,
    prof_promedio
FROM resumen_huerfanos
ORDER BY pasivo_total_usd DESC
LIMIT 10;


-- --------------------------------------------------------------------
-- 8. Window Functions: Deepest Producing Well by Region
-- Concepts: ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)
-- Business insight: Extracts record-depth exploratory targets without collapsing rows.
-- --------------------------------------------------------------------
WITH ranking_pozos AS (
    SELECT 
        condado,
        api,
        nombre_arrendamiento,
        nombre_campo,
        profundidad_pies,
        ROW_NUMBER() OVER (
            PARTITION BY condado 
            ORDER BY profundidad_pies DESC
        ) AS puesto_en_condado
    FROM pozos_texas
    WHERE profundidad_pies > 0
      AND condado IN ('Midland', 'Reeves', 'Harris', 'Pecos', 'Karnes')
)
SELECT 
    condado,
    api AS api_pozo,
    nombre_arrendamiento AS nombre_pozo,
    nombre_campo AS formacion_geologica,
    profundidad_pies
FROM ranking_pozos
WHERE puesto_en_condado = 1
ORDER BY profundidad_pies DESC;


-- --------------------------------------------------------------------
-- 9. Downstream Market Share: Top Texas Refining Corporations (EIA-820)
-- Concepts: Capacity aggregation, global market share percentage subquery
-- Business insight: Motiva, Marathon, and ExxonMobil control the Gulf Coast refining hub.
-- --------------------------------------------------------------------
SELECT 
    corporacion,
    COUNT(*) AS total_refinerias,
    SUM(capacidad_barriles_dia_calendario) AS capacidad_total_bpd,
    ROUND(
        SUM(capacidad_barriles_dia_calendario) * 100.0 / 
        (SELECT SUM(capacidad_barriles_dia_calendario) FROM refinerias_texas), 
        2
    ) AS cuota_mercado_pct
FROM refinerias_texas
GROUP BY corporacion
ORDER BY capacidad_total_bpd DESC
LIMIT 10;


-- --------------------------------------------------------------------
-- 10. Regional Refining Capacity: Texas Gulf Coast vs Inland
-- Concepts: Aggregations with facility counts and plant capacity averages
-- Business insight: Measures coastal concentration of crude processing infrastructure.
-- --------------------------------------------------------------------
SELECT 
    distrito_refinacion,
    COUNT(*) AS numero_plantas,
    SUM(capacidad_barriles_dia_calendario) AS capacidad_total_bpd,
    ROUND(AVG(capacidad_barriles_dia_calendario), 0) AS capacidad_promedio_planta_bpd
FROM refinerias_texas
GROUP BY distrito_refinacion
ORDER BY capacidad_total_bpd DESC;


-- --------------------------------------------------------------------
-- 11. Year-over-Year Production Growth Analysis: Window LAG() Function
-- Concepts: LAG() OVER (ORDER BY ...), Year-over-Year growth percentage
-- Business insight: Evaluates post-shale expansion rates in Texas oil production.
-- --------------------------------------------------------------------
WITH produccion_anual AS (
    SELECT 
        SUBSTR(fecha, 1, 4) AS anio,
        SUM(miles_barriles) AS total_miles_barriles,
        ROUND(AVG(miles_barriles), 1) AS promedio_mensual_miles_barriles
    FROM produccion_texas_mensual
    GROUP BY SUBSTR(fecha, 1, 4)
)
SELECT 
    anio,
    total_miles_barriles,
    LAG(total_miles_barriles) OVER (ORDER BY anio) AS produccion_anio_anterior,
    ROUND(
        (total_miles_barriles - LAG(total_miles_barriles) OVER (ORDER BY anio)) * 100.0 / 
        LAG(total_miles_barriles) OVER (ORDER BY anio), 2
    ) AS crecimiento_interanual_pct
FROM produccion_anual
ORDER BY anio DESC
LIMIT 15;


-- --------------------------------------------------------------------
-- 12. Rolling 30-Day Moving Averages & Volatility Bands
-- Concepts: Rolling window frames (ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
-- Business insight: Essential financial technique for oil trading and price trend smoothing.
-- --------------------------------------------------------------------
WITH precios_filtrados AS (
    SELECT 
        fecha,
        precio_wti_usd,
        precio_brent_usd,
        spread_brent_wti
    FROM precios_crudo_diario
    WHERE precio_wti_usd IS NOT NULL
),
promedios_moviles AS (
    SELECT 
        fecha,
        precio_wti_usd,
        ROUND(AVG(precio_wti_usd) OVER (ORDER BY fecha ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS media_movil_30d,
        ROUND(MIN(precio_wti_usd) OVER (ORDER BY fecha ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS minimo_30d,
        ROUND(MAX(precio_wti_usd) OVER (ORDER BY fecha ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS maximo_30d,
        spread_brent_wti
    FROM precios_filtrados
)
SELECT *
FROM promedios_moviles
ORDER BY fecha DESC
LIMIT 20;


-- --------------------------------------------------------------------
-- 13. Environmental Risk vs Financial Assurance: Bond Coverage
-- Concepts: Cross-table filtering, multi-column sorting, financial liability audit
-- Business insight: Flags operators with high inactive well counts against pledged surety bonds.
-- --------------------------------------------------------------------
SELECT 
    o.ciudad,
    o.nombre AS operador,
    o.tipo_organizacion,
    o.estado_licencia,
    o.garantia_financiera_usd,
    COUNT(p.api) AS pozos_inactivos_asociados
FROM operadores_texas o
INNER JOIN pozos_texas p ON o.operador_id = p.operador_id
WHERE o.garantia_financiera_usd > 0
GROUP BY o.operador_id, o.nombre
ORDER BY o.garantia_financiera_usd DESC, pozos_inactivos_asociados DESC
LIMIT 12;


-- --------------------------------------------------------------------
-- 14. Regulatory District Breakdown: Inactive Wells by Resource & Status
-- Concepts: Conditional aggregation with SUM(CASE WHEN ... THEN 1 ELSE 0 END)
-- Business insight: Cross-tabulates oil vs gas vs orphan wells per RRC administrative district.
-- --------------------------------------------------------------------
SELECT 
    distrito_rrc,
    COUNT(*) AS total_pozos,
    ROUND(AVG(profundidad_pies), 0) AS profundidad_media,
    SUM(CASE WHEN tipo_recurso = 'Petróleo' THEN 1 ELSE 0 END) AS pozos_petroleo,
    SUM(CASE WHEN tipo_recurso = 'Gas' THEN 1 ELSE 0 END) AS pozos_gas,
    SUM(es_pozo_huerfano) AS total_pozos_huerfanos
FROM pozos_texas
WHERE distrito_rrc IS NOT NULL
GROUP BY distrito_rrc
ORDER BY total_pozos DESC;
