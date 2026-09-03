-- ====================================================================
-- 🛢️ BITÁCORA DE CONSULTAS: APRENDIZAJE SQL (HOUSTON & TEXAS ENERGY)
-- Base de Datos: houston_energy.db (~190,000 registros reales)
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Pozos por condado (Volumen y Profundidad)
-- Conceptos: COUNT, AVG, MAX, GROUP BY, ORDER BY, LIMIT.
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
-- 2. Filtrando por Gas y Profundidad (Detección de outliers)
-- Conceptos: WHERE con múltiples condiciones.
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
-- 3. Eliminando sesgos con HAVING: Los verdaderos campos de gas
-- Conceptos: HAVING para filtrar métricas después de agrupar.
-- Resultado: Robertson se corona como el rey del gas profundo (14,428 ft).
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
-- 4. El poder del INNER JOIN: Grandes operadoras de Houston
-- Conceptos: INNER JOIN, alias (o, p), llaves foráneas (operador_id).
-- Resultado: Apache lidera en crudo (2,181 pozos) y Hilcorp en gas (1,687).
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
-- 5. Series de Tiempo: Historia económica del WTI (1986 - Hoy)
-- Conceptos: SUBSTR(fecha), MIN, MAX, promedios anuales.
-- Hallazgo: 2020 registró el precio mínimo histórico (-36.98 USD).
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
-- 6. Segmentación con CASE WHEN: Clasificación técnica y costos
-- Conceptos: CASE WHEN, subconsulta de porcentaje dinámico.
-- Hallazgo: Ultra-profundo (>9,000 ft) cuesta 7x más remediar que somero.
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
-- 7. Análisis con CTE (WITH): Pasivo ambiental de Pozos Huérfanos
-- Conceptos: WITH ... AS (Tablas temporales en memoria).
-- Hallazgo: Pecos lidera con $14.73 millones USD en pasivo ambiental.
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
-- 8. Funciones de Ventana: El pozo más profundo por condado
-- Conceptos: ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...).
-- Hallazgo: Harris (Houston) tiene récord en formación Wilcox a 18,034 ft.
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
