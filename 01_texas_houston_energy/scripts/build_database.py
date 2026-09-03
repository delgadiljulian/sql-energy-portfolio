"""Reconstrucción offline: valida las fuentes, carga en una base temporal y sustituye al final."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from download_sources import ROOT, DATA, sha, atomic_json

DB = DATA / "houston_energy_v2.db"

def code_fingerprint():
    h = hashlib.sha256()
    files = [ROOT/"scripts/download_sources.py", ROOT/"scripts/build_database.py", ROOT/"sql/schema.sql"]
    for p in files:
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()

def register_legacy():
    path = DATA / "legacy_sources.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["fuentes"]
    details = {
        "rrc_pozos_texas.csv": ("rrc_iwar_historico", "iwar", "observado_heredado", "analitico", "registro administrativo",
            "Archivo heredado sin recibo de descarga. Todos los meses de cierre más la antigüedad indican 2020-10; fecha inferida, no publicación verificada."),
        "rrc_operadores_texas.csv": ("rrc_p5_historico", "p5", "observado_heredado", "analitico", "organización P-5",
            "Archivo heredado sin fecha de corte ni URL de descarga verificadas. Incluye organizaciones inactivas. Sus direcciones y estados no se afirman actuales."),
        "produccion_cuencas_texas.csv": ("demo_cuencas", "demo", "simulado", "didactico", "condado-cuenca-mes",
            "Generado por fórmula en la versión inicial; no es producción observada de la RRC."),
        "empresas_energia_houston.csv": ("archivo_empresas", "archivo", "manual_no_verificado", "archivo", "empresa",
            "Cifras escritas manualmente sin referencia individual ni año fiscal; no se cargan como datos analíticos."),
        "refinerias_texas_coast.csv": ("archivo_refinerias", "archivo", "manual_no_verificado", "archivo", "refinería",
            "Catálogo inicial sustituido en el modelo por la encuesta EIA-820."),
        "terminales_houston_ship_channel.csv": ("archivo_terminales", "archivo", "manual_no_verificado", "archivo", "terminal",
            "Datos manuales sin trazabilidad individual; se conservan únicamente como archivo."),
        "precios_wti_mensual.csv": ("archivo_wti_mensual", "archivo", "observado_heredado", "archivo", "USD/barril",
            "Serie inicial descargada de datasets/oil-prices; se conserva como archivo."),
        "precios_wti_diario.csv": ("archivo_wti_diario", "archivo", "observado_heredado", "archivo", "USD/barril",
            "Serie heredada sustituida por descarga directa de la EIA."),
        "precios_brent_diario.csv": ("archivo_brent_diario", "archivo", "observado_heredado", "archivo", "USD/barril",
            "Serie heredada sustituida por descarga directa de la EIA."),
    }
    sources = []
    for filename, (sid, kind, nature, use, unit, note) in details.items():
        f = DATA / "raw" / filename
        with f.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            next(reader)
            n = sum(1 for _ in reader)
        sources.append({
            "id": sid, "titulo": filename, "tipo": kind, "naturaleza": nature, "uso": use,
            "unidad": unit, "archivo": f.relative_to(ROOT).as_posix(), "sha256": sha(f), "filas": n,
            "url_descarga": None, "descargado_utc": None, "fecha_corte": None,
            "periodo_inferido": "2020-10" if kind == "iwar" else None, "notas": note,
            "url_referencia": "https://www.rrc.texas.gov/media/1rvacfwr/iwar_downloadfilejune11.pdf" if kind == "iwar"
                else ("https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/" if kind == "p5" else None),
        })
    atomic_json(path, {"version": 1, "registrado_utc": datetime.now(timezone.utc).isoformat(), "fuentes": sources})
    return sources

def load_sources():
    official = DATA / "official_sources.json"
    if not official.exists():
        raise ValueError("Falta official_sources.json. Ejecuta scripts/download_sources.py con las dependencias instaladas.")
    sources = register_legacy() + json.loads(official.read_text(encoding="utf-8"))["fuentes"]
    ids = set()
    for s in sources:
        if s["id"] in ids:
            raise ValueError("Fuente repetida: " + s["id"])
        ids.add(s["id"])
        for pk, hk in [("archivo", "sha256"), ("archivo_original", "sha256_original")]:
            if pk in s:
                p = (ROOT / s[pk]).resolve()
                if not p.is_relative_to(ROOT.resolve()):
                    raise ValueError("Ruta de fuente fuera del proyecto")
                if sha(p) != s[hk]:
                    raise ValueError("La fuente cambió respecto al manifiesto: " + s[pk])
    return sources

def records(source, required):
    with (ROOT / source["archivo"]).open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=source.get("delimitador", ","))
        if not required.issubset(r.fieldnames or []):
            raise ValueError(f"Columnas faltantes en {source['id']}: {sorted(required - set(r.fieldnames or []))}")
        count = 0
        for line, row in enumerate(r, start=2):
            if None in row:
                raise ValueError(f"Columnas adicionales sin encabezado en {source['id']}, fila {line}")
            count += 1
            yield line, {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
        if count != source["filas"]:
            raise ValueError(f"Conteo de archivo distinto al manifiesto: {source['id']}")

def integer(value):
    try:
        n = Decimal(str(value))
    except InvalidOperation as e:
        raise ValueError("Entero inválido: " + str(value)) from e
    if not n.is_finite() or n != n.to_integral_value():
        raise ValueError("Entero inválido: " + str(value))
    return int(n)

def identifier(value, width):
    s = str(value).strip()
    if not s.isascii() or not s.isdigit() or len(s) > width:
        raise ValueError("Identificador inválido: " + s)
    return s.zfill(width)

def add_incident(c, sid, line, field, value, reason):
    c.execute("INSERT INTO incidencias_carga(fuente_id,fila_origen,campo,valor_original,motivo) VALUES (?,?,?,?,?)",
              (sid, line, field, str(value), reason))

def optional_date(c, sid, line, field, value, monthly=False, american=False):
    if not value or value == "0":
        add_incident(c, sid, line, field, value, "Fecha no informada; se conserva NULL")
        return None
    try:
        if monthly:
            return datetime.strptime(value, "%Y%m").date().replace(day=1).isoformat()[:7]
        return datetime.strptime(value, "%m/%d/%Y" if american else "%Y%m%d").date().isoformat()
    except ValueError:
        add_incident(c, sid, line, field, value, "Fecha inválida; se conserva NULL")
        return None

def optional_number(value):
    if value is None or value == "":
        return None
    n = float(value)
    if not math.isfinite(n):
        raise ValueError("Valor no finito: " + str(value))
    return n

def flag(value):
    if value is None or value == "":
        return None
    mapping = {"Y": 1, "N": 0, "TRUE": 1, "FALSE": 0}
    if value not in mapping:
        raise ValueError("Indicador inesperado: " + value)
    return mapping[value]

def import_p5(c, source):
    required = {"Operator Number", "Operator Name", "Org-P5 Status", "Org Type",
                "Location Address City", "Location Address State", "Location Address Zip",
                "FA Amount", "FA Option", "FA Type", "Last P5 Filed Date"}
    for line, r in records(source, required):
        oid = identifier(r["Operator Number"], 6)
        c.execute("INSERT INTO operadores VALUES (?) ON CONFLICT(operador_id) DO NOTHING", (oid,))
        last = optional_date(c, source["id"], line, "Last P5 Filed Date", r["Last P5 Filed Date"], american=True)
        c.execute("INSERT INTO operadores_p5_historico VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, source["id"], r["Operator Name"], r["Org-P5 Status"], r["Org Type"],
             r["Location Address City"].upper() or None, r["Location Address State"].upper() or None,
             r["Location Address Zip"] or None, optional_number(r["FA Amount"]),
             r["FA Option"] or None, r["FA Type"] or None, last))

def import_iwar(c, source):
    required = {"Operator Number", "Operator Name", "API County Number", "API Unique Number",
                "County Name", "District Code", "O/G Code", "Lease Number", "Well Number",
                "Field Number", "Field Name", "API Depth", "Shut In Date", "Current Inactive Years",
                "Current Inactive Months", "Cost Calculation", "Well Plugged", "Original Completion Date"}
    sid = source["id"]
    for line, r in records(source, required):
        api8 = identifier(r["API County Number"], 3) + identifier(r["API Unique Number"], 5)
        if r.get("API") and identifier(r["API"], 8) != api8:
            raise ValueError(f"API y componentes no concuerdan: {sid}, fila {line}")
        oid = identifier(r["Operator Number"], 6)
        c.execute("INSERT INTO operadores VALUES (?) ON CONFLICT(operador_id) DO NOTHING", (oid,))
        district = r["District Code"].upper()
        if district.isdigit():
            district = district.zfill(2)
        depth = integer(r["API Depth"]) if r["API Depth"] else None
        if depth is not None and depth <= 0:
            add_incident(c, sid, line, "API Depth", r["API Depth"], "Profundidad no positiva; se conserva NULL")
            depth = None
        original_date = optional_date(c, sid, line, "Original Completion Date", r["Original Completion Date"])
        closed = optional_date(c, sid, line, "Shut In Date", r["Shut In Date"], monthly=True)
        months_part = integer(r["Current Inactive Months"])
        if not 0 <= months_part <= 11:
            raise ValueError(f"Meses de inactividad fuera de rango: {sid}, fila {line}")
        age = 12 * integer(r["Current Inactive Years"]) + months_part
        inferred = None
        if closed:
            yy, mm = map(int, closed.split("-"))
            total = yy * 12 + mm - 1 + age
            inferred = f"{total // 12:04d}-{total % 12 + 1:02d}"
        resource = {"O": "Petróleo", "G": "Gas", "B": "Mixto"}.get(r["O/G Code"])
        if not resource:
            raise ValueError(f"Código de recurso inesperado: {sid}, fila {line}")
        values = (sid, line, "42" + api8, r.get("API"), oid, r["Operator Name"],
                  r["County Name"].title(), district, resource, r["Lease Number"],
                  r["Well Number"], r.get("Oil Unit Number"), r.get("Lease Name"), r["Field Number"],
                  r["Field Name"], depth, original_date, closed, age, inferred,
                  optional_number(r["Cost Calculation"]), flag(r["Well Plugged"]),
                  flag(r.get("Is Orphan?")), r.get("Extension Status"))
        c.execute("""INSERT INTO pozos_inactivos_registros(
          fuente_id,fila_origen,api,api_original,operador_id,operador_nombre,condado,distrito_rrc,
          tipo_recurso,numero_arrendamiento,numero_pozo,unidad_petrolera,nombre_arrendamiento,
          numero_campo,nombre_campo,profundidad_pies,fecha_registro_original,mes_cierre,
          meses_inactivo,mes_corte_inferido,costo_taponamiento_estimado_usd,taponamiento_reportado,
          es_pozo_huerfano,estado_extension) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)

def import_other(c, source):
    sid = source["id"]
    if source["tipo"] in ("precio", "produccion"):
        for _, r in records(source, {"fecha", "valor"}):
            d = date.fromisoformat(r["fecha"])
            if d > date.today():
                raise ValueError("Observación futura en " + sid)
            if source["tipo"] == "precio":
                c.execute("INSERT INTO precios_observaciones VALUES (?,?,?,?)",
                          (sid, "WTI" if sid == "eia_wti" else "BRENT", r["fecha"], optional_number(r["valor"])))
            else:
                c.execute("INSERT INTO produccion_texas_mensual VALUES (?,?,?)", (r["fecha"], sid, integer(r["valor"])))
    elif source["tipo"] == "refinerias":
        for _, r in records(source, {"fecha_corte", "corporacion", "operador", "localidad",
                                    "distrito_refinacion", "padd", "capacidad_bcd"}):
            c.execute("""INSERT INTO refinerias_texas(fuente_id,fecha_corte,corporacion,operador,
                localidad,distrito_refinacion,padd,capacidad_barriles_dia_calendario) VALUES (?,?,?,?,?,?,?,?)""",
                (sid, r["fecha_corte"], r["corporacion"], r["operador"], r["localidad"],
                 r["distrito_refinacion"], r["padd"], integer(r["capacidad_bcd"])))
    elif source["tipo"] == "demo":
        fields = ["cuenca", "condado", "region", "anio", "mes", "barriles_crudo_mes", "mcf_gas_mes", "pozos_productivos"]
        for _, r in records(source, set(fields)):
            c.execute("INSERT INTO demo_produccion_cuencas VALUES (?,'simulado',?,?,?,?,?,?,?,?)",
                (sid, r["cuenca"], r["condado"], r["region"], *(integer(r[k]) for k in fields[3:])))

def consolidate_iwar(c):
    c.execute("""INSERT INTO pozos_inactivos
    SELECT fuente_id,api,COUNT(*),COUNT(DISTINCT operador_id),
           CASE WHEN COUNT(DISTINCT operador_id)=1 THEN MIN(operador_id) END,
           CASE WHEN COUNT(DISTINCT operador_nombre)=1 THEN MIN(operador_nombre) END,
           CASE WHEN COUNT(DISTINCT condado)=1 THEN MIN(condado) END,
           COUNT(DISTINCT distrito_rrc),
           CASE WHEN COUNT(DISTINCT distrito_rrc)=1 THEN MIN(distrito_rrc) END,
           CASE WHEN COUNT(DISTINCT tipo_recurso)=1 THEN MIN(tipo_recurso) ELSE 'Mixto' END,
           COUNT(DISTINCT numero_campo),
           CASE WHEN COUNT(DISTINCT profundidad_pies)=1 THEN MIN(profundidad_pies) END,
           CASE WHEN COUNT(DISTINCT meses_inactivo)=1 THEN MIN(meses_inactivo) END,
           CASE WHEN COUNT(DISTINCT costo_taponamiento_estimado_usd)=1
                THEN MIN(costo_taponamiento_estimado_usd) END,
           CASE WHEN COUNT(DISTINCT taponamiento_reportado)=1 THEN MIN(taponamiento_reportado) END,
           CASE WHEN COUNT(DISTINCT es_pozo_huerfano)=1 THEN MIN(es_pozo_huerfano) END
    FROM pozos_inactivos_registros GROUP BY fuente_id,api""")

def audit(c, sources):
    failures = []
    checks = []
    def check(name, success, detail):
        checks.append({"control": name, "ok": bool(success), "detalle": detail})
        if not success:
            failures.append(name)
    integrity = c.execute("PRAGMA integrity_check").fetchall()
    check("integridad_sqlite", integrity == [("ok",)], str(integrity))
    foreign = c.execute("PRAGMA foreign_key_check").fetchall()
    check("claves_foraneas", not foreign, len(foreign))
    table_for = {"p5": "operadores_p5_historico", "iwar": "pozos_inactivos_registros",
                 "precio": "precios_observaciones", "produccion": "produccion_texas_mensual",
                 "refinerias": "refinerias_texas", "demo": "demo_produccion_cuencas"}
    for s in sources:
        stored = c.execute("SELECT sha256 FROM fuentes WHERE fuente_id=?", (s["id"],)).fetchone()
        check("huella_" + s["id"], stored == (s["sha256"],), "Manifiesto y base deben representar el mismo archivo")
        if s["tipo"] not in table_for:
            continue
        n = c.execute(f"SELECT COUNT(*) FROM {table_for[s['tipo']]} WHERE fuente_id=?", (s["id"],)).fetchone()[0]
        check("filas_" + s["id"], n == s["filas"], {"origen": s["filas"], "cargadas": n})
        if s["tipo"] == "iwar":
            expected = s.get("periodo_inferido") or s["fecha_corte"][:7]
            mismatches = c.execute("SELECT COUNT(*) FROM pozos_inactivos_registros WHERE fuente_id=? AND (mes_corte_inferido IS NULL OR mes_corte_inferido!=?)",
                                   (s["id"], expected)).fetchone()[0]
            check("corte_" + s["id"], mismatches == 0, {"mes": expected, "discordantes": mismatches})
    missing_district = c.execute("SELECT COUNT(*) FROM pozos_inactivos_registros WHERE distrito_rrc IS NULL").fetchone()[0]
    check("distritos_completos", missing_district == 0, missing_district)
    months = [r[0] for r in c.execute("SELECT fecha FROM produccion_texas_mensual ORDER BY fecha")]
    gaps = []
    for a, b in zip(months, months[1:]):
        y, m = int(a[:4]), int(a[5:7])
        expected = f"{y + (m == 12):04d}-{m % 12 + 1:02d}-01"
        if b != expected:
            gaps.append([a,b])
    check("produccion_meses_consecutivos", bool(months) and not gaps, gaps)
    simulated = c.execute("""SELECT COUNT(*) FROM demo_produccion_cuencas d
         JOIN fuentes f USING(fuente_id) WHERE f.naturaleza!='simulado' OR d.naturaleza!='simulado'""").fetchone()[0]
    check("separacion_datos_simulados", simulated == 0, simulated)
    if failures:
        raise ValueError("Validación fallida: " + ", ".join(failures) + "\n" + json.dumps(checks, ensure_ascii=False))
    tables = {r[0]: c.execute(f'SELECT COUNT(*) FROM "{r[0]}"').fetchone()[0]
              for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    def rows(sql):
        cur = c.execute(sql)
        headers = [x[0] for x in cur.description]
        return [dict(zip(headers, row)) for row in cur.fetchall()]
    summary = {
        "controles": checks, "tablas": tables,
        "pozos_por_fuente": rows("""SELECT fuente_id,COUNT(*) api_distintos,SUM(registros_por_api) registros,
            SUM(registros_por_api>1) api_con_varios_registros,SUM(n_operadores>1) api_con_varios_operadores,
            SUM(n_distritos>1) api_con_varios_distritos,SUM(profundidad_pies IS NULL) profundidad_no_disponible
            FROM vw_pozos_inactivos GROUP BY fuente_id"""),
        "incidencias": rows("SELECT fuente_id,campo,motivo,COUNT(*) n FROM incidencias_carga GROUP BY 1,2,3"),
        "precios": rows("SELECT referencia,COUNT(*) filas,MIN(fecha) inicio,MAX(fecha) fin,SUM(precio_usd_barril IS NULL) ausentes FROM precios_observaciones GROUP BY referencia"),
        "produccion": rows("SELECT COUNT(*) meses,MIN(fecha) inicio,MAX(fecha) fin FROM produccion_texas_mensual"),
    }
    return summary

def save_report(report, destination):
    destination.mkdir(parents=True, exist_ok=True)
    atomic_json(destination / "validacion.json", report)
    lines = ["# Validación de la base", "", f"Carga: {report['carga_id']}",
             f"UTC: {report['iniciado_utc']}", "",
             f"Controles obligatorios aprobados: {len(report['controles'])}.", "",
             "## Registros y API por corte", "",
             "| Fuente | Registros conservados | API distintos | API con varios operadores |",
             "|---|---:|---:|---:|"]
    for r in report["pozos_por_fuente"]:
        lines.append(f"| {r['fuente_id']} | {r['registros']} | {r['api_distintos']} | {r['api_con_varios_operadores']} |")
    lines.extend(["", "Las filas repetidas por API se conservan. La vista por API deja en NULL los atributos contradictorios.",
                  "El corte heredado 2020-10 es inferido. El corte oficial actual consta en official_sources.json.",
                  "El P-5 heredado no certifica sedes ni estados actuales.", "", "## Incidencias de normalización", "",
                  "| Fuente | Campo | Motivo | Filas |", "|---|---|---|---:|"])
    for r in report["incidencias"]:
        lines.append(f"| {r['fuente_id']} | {r['campo']} | {r['motivo']} | {r['n']} |")
    lines += ["", "Los originales permanecen intactos; cada incidencia apunta a su fuente y fila.",
              "No se sustituyen números ausentes por cero. Los precios negativos observados se conservan.",
              "", "Detalle reproducible: validacion.json y consultas/00_calidad_datos.sql.", ""]
    (destination / "VALIDACION.md").write_text("\n".join(lines), encoding="utf-8")

def build(output=DB, reports=None):
    sources = load_sources()  # Toda la verificación de archivos precede a la creación temporal.
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline = sha(output) if output.exists() else None
    started = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    model_hash = code_fingerprint()
    # Solo se elimina el archivo temporal concreto creado por esta ejecución.
    fd, tmp_name = tempfile.mkstemp(prefix=".build_", suffix=".db", dir=output.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    c = None
    backup = None
    try:
        c = sqlite3.connect(tmp)
        c.execute("PRAGMA foreign_keys=ON")
        c.executescript((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        c.execute("BEGIN")
        for s in sources:
            c.execute("INSERT INTO fuentes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (s["id"],s["titulo"],s["naturaleza"],s["uso"],s.get("fecha_corte"),
                 s.get("periodo_inicio"),s.get("periodo_fin"),s["unidad"],s["archivo"],
                 s["sha256"],s["filas"],json.dumps(s,ensure_ascii=False)))
        for kind in ("p5", "iwar", "precio", "produccion", "refinerias", "demo"):
            for s in sources:
                if s["tipo"] != kind:
                    continue
                print(f"Cargando {s['id']} ({s['filas']:,} filas)...", flush=True)
                if kind == "p5":
                    import_p5(c, s)
                elif kind == "iwar":
                    import_iwar(c, s)
                else:
                    import_other(c, s)
        consolidate_iwar(c)
        report = audit(c, sources)
        report.update({"carga_id":run_id,"iniciado_utc":started,"huella_codigo":model_hash})
        c.execute("INSERT INTO ejecucion_carga VALUES (?,?,?,?,?,?)",
                  (run_id,started,sqlite3.sqlite_version,2,model_hash,"validado"))
        report["tablas"]["ejecucion_carga"] = 1
        c.commit()
        c.execute("ANALYZE")
        c.close()
        c = None
        if (sha(output) if output.exists() else None) != baseline:
            raise ValueError("La base cambió durante la carga; se conserva la versión modificada externamente.")
        if output.exists():
            backup_dir = output.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            backup = backup_dir / f"{output.stem}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.db"
            # backup() también captura una base que esté usando WAL.
            with closing(sqlite3.connect(output.as_uri() + "?mode=ro", uri=True)) as old, closing(sqlite3.connect(backup)) as dest:
                old.backup(dest)
            for suffix in ("-wal", "-shm", "-journal"):
                if Path(str(output) + suffix).exists():
                    raise ValueError("Cierra las conexiones de escritura a la base antes de sustituirla.")
        os.replace(tmp, output)
        report["base"] = output.name
        report["respaldo"] = str(backup) if backup else None
        if reports is not None:
            save_report(report, Path(reports))
        return report
    finally:
        if c:
            c.close()
        if tmp.exists():
            tmp.unlink()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=DB)
    args = p.parse_args()
    try:
        report = build(args.salida, ROOT / "outputs")
        print(f"Base reconstruida y validada. Controles: {len(report['controles'])}.")
    except Exception as exc:
        p.exit(1, f"ERROR: {exc}\nNo se reemplaza una base con una carga que falle la validación.\n")

if __name__ == "__main__":
    main()
