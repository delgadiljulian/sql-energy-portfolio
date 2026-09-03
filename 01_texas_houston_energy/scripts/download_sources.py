"""Descarga archivos oficiales; publica el manifiesto solo tras convertir y validar el lote."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PORTAL_IWAR = "https://www.rrc.texas.gov/oil-and-gas/compliance-enforcement/hb-2259hb-3134-inactive-well-requirements/inactive-well-aging-report-iwar/"
REF_PORTAL = "https://www.eia.gov/petroleum/refinerycapacity/"
SERIES = {
    "eia_wti": ("wti_diario.xls", "RWTC", "WTI spot Cushing, Oklahoma", "USD/barril", "D"),
    "eia_brent": ("brent_diario.xls", "RBRTE", "Brent spot Europa", "USD/barril", "D"),
    "eia_produccion_texas": ("produccion_texas_mensual.xls", "MCRFPTX1", "Producción mensual de crudo de Texas", "miles de barriles/mes", "m"),
}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".manifest_", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def fetch(url, target):
    req = Request(url, headers={"User-Agent": "TexasEnergySQL/2.0 (public research)"})
    with urlopen(req, timeout=45) as r:
        body = r.read(100 * 1024 * 1024 + 1)
        resolved = r.url
    if not body or len(body) > 100 * 1024 * 1024:
        raise ValueError("Descarga vacía o mayor al límite de 100 MB: " + url)
    target.write_bytes(body)
    return {"file": target.name, "url": url, "resolved_url": resolved,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha(target), "bytes": len(body)}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == "a" and dict(attrs).get("href"):
            self.hrefs.append(dict(attrs)["href"])

def linked_file(page, pattern):
    links = Links()
    links.feed(page)
    matches = [h for h in links.hrefs if re.search(pattern, h, re.I)]
    if len(set(matches)) != 1:
        raise ValueError("No se pudo identificar un único archivo oficial: " + pattern)
    return matches[0]

def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        w.writerows(rows)

def convert(batch, downloads):
    # Dependencias opcionales: no se importan al reconstruir la base offline.
    import xlrd
    import openpyxl
    byfile = {d["file"]: d for d in downloads}
    sources = []
    def entry(sid, title, filename, output, count, reference, unit, **extra):
        d = byfile[filename]
        if sha(batch / filename) != d["sha256"]:
            raise ValueError("Cambió el archivo descargado: " + filename)
        sources.append({
            "id": sid, "titulo": title, "naturaleza": "observado_oficial",
            "tipo": extra.pop("tipo"), "uso": "analitico", "unidad": unit,
            "archivo": (batch / output).relative_to(ROOT).as_posix(),
            "sha256": sha(batch / output), "filas": count,
            "archivo_original": (batch / filename).relative_to(ROOT).as_posix(),
            "sha256_original": d["sha256"], "url_descarga": d["url"],
            "url_referencia": reference, "descargado_utc": d["downloaded_at"],
            **extra,
        })
    for sid, (filename, code, title, unit, frequency) in SERIES.items():
        w = xlrd.open_workbook(batch / filename)
        s = w.sheet_by_name("Data 1")
        if s.cell_value(1, 1) != code or s.cell_value(2, 0) != "Date":
            raise ValueError("Cambió el esquema o identificador EIA: " + filename)
        values = []
        seen = set()
        for i in range(3, s.nrows):
            dt, value = s.row_values(i)[:2]
            if dt == "":
                continue
            if s.cell_type(i, 0) != xlrd.XL_CELL_DATE:
                raise ValueError(f"Fecha inesperada en {filename}, fila {i + 1}")
            d = xlrd.xldate_as_datetime(dt, w.datemode).date()
            if sid == "eia_produccion_texas":
                d = d.replace(day=1)
            if d in seen:
                raise ValueError("Fecha duplicada en " + filename)
            seen.add(d)
            if value != "" and not isinstance(value, (int, float)):
                raise ValueError("Valor EIA no numérico: " + str(value))
            values.append((d.isoformat(), value))
        if len(values) < 100:
            raise ValueError("Serie EIA incompleta: " + filename)
        values.sort()
        output = sid + ".csv"
        write_csv(batch / output, ["fecha", "valor"], values)
        entry(sid, title, filename, output, len(values),
              f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={code}&f={frequency.upper()}",
              unit, tipo="produccion" if sid == "eia_produccion_texas" else "precio",
              periodo_inicio=values[0][0], periodo_fin=values[-1][0],
              fecha_corte=None, codigo_serie=code)

    ref_files = [x for x in byfile if re.fullmatch(r"refcap\d{2}\.xlsx", x)]
    if len(ref_files) != 1:
        raise ValueError("Se requiere un solo archivo EIA-820")
    filename = ref_files[0]
    year = 2000 + int(filename[6:8])
    w = openpyxl.load_workbook(batch / filename, read_only=True, data_only=True)
    allrows = iter(w.active.values)
    headers = next(allrows)
    expected = {"CORPORATION", "SURVEY", "PERIOD", "COMPANY_NAME", "RDIST_LABEL",
                "STATE_NAME", "SITE", "PADD", "PRODUCT", "SUPPLY", "QUANTITY"}
    if not expected.issubset(headers):
        raise ValueError("Cambió el esquema EIA-820")
    records = []
    keys = set()
    for row in allrows:
        r = dict(zip(headers, row))
        if r["STATE_NAME"] != "Texas":
            continue
        if (r["PRODUCT"] != "TOTAL OPERABLE CAPACITY" or
            r["SUPPLY"] != "Atmospheric Crude Distillation Capacity (barrels per calendar day)"):
            continue
        if str(r["PERIOD"]).zfill(2) != str(year)[2:] or str(r["SURVEY"]) != "820":
            raise ValueError("Año o encuesta EIA inesperado")
        key = (r["COMPANY_NAME"], r["SITE"])
        if key in keys:
            raise ValueError("La clave empresa/localidad no identifica una refinería única")
        keys.add(key)
        records.append((f"{year}-01-01", r["CORPORATION"], r["COMPANY_NAME"], r["SITE"],
                        r["RDIST_LABEL"], r["PADD"], r["QUANTITY"]))
    w.close()
    if len(records) < 10:
        raise ValueError("Archivo de refinerías incompleto")
    write_csv(batch / "eia_refinerias_texas.csv",
              ["fecha_corte", "corporacion", "operador", "localidad", "distrito_refinacion", "padd", "capacidad_bcd"],
              sorted(records))
    entry("eia_refinerias_texas", "Capacidad operable de destilación atmosférica de crudo, Texas",
          filename, "eia_refinerias_texas.csv", len(records), REF_PORTAL,
          "barriles/día calendario", tipo="refinerias", fecha_corte=f"{year}-01-01")

    iwarfiles = [x for x in byfile if re.fullmatch(r"rrc_iwar_\d{8}\.txt", x)]
    if len(iwarfiles) != 1:
        raise ValueError("Se requiere un único corte IWAR oficial")
    filename = iwarfiles[0]
    with (batch / filename).open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        if not {"Operator Number", "API County Number", "API Unique Number",
                "District Code", "Shut In Date"}.issubset(r.fieldnames or []):
            raise ValueError("Cambió el esquema del IWAR")
        count = sum(1 for _ in r)
    if count < 1000:
        raise ValueError("Archivo IWAR incompleto")
    cutoff = datetime.strptime(filename[9:17], "%Y%m%d").date().isoformat()
    entry("rrc_iwar_actual", "IWAR oficial: registros de pozos inactivos de Texas",
          filename, filename, count, PORTAL_IWAR, "registro administrativo",
          tipo="iwar", fecha_corte=cutoff, delimitador="\t",
          notas="El archivo TXT actual no incluye Is Orphan?: se conserva NULL. No representa todos los pozos de Texas.")
    return sources

def update(refresh=False):
    manifest = DATA / "fuentes_oficiales.json"
    if manifest.exists() and not refresh:
        for s in json.loads(manifest.read_text(encoding="utf-8"))["fuentes"]:
            for p, h in [("archivo", "sha256"), ("archivo_original", "sha256_original")]:
                if sha(ROOT / s[p]) != s[h]:
                    raise ValueError("Hash de fuente distinto al manifiesto: " + s[p])
        print("Fuentes oficiales locales verificadas; no se requiere descarga.")
        return
    # Importa únicamente el lote descargado durante la recuperación inicial, con recibos y hashes.
    seed = DATA / "raw/oficiales"
    if not refresh and (seed / "descargas_iniciales.json").exists():
        batch = seed
        downloads = json.loads((seed / "descargas_iniciales.json").read_text(encoding="utf-8"))
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        batch = seed / ("lote_" + stamp)
        batch.mkdir(parents=True)
        downloads = []
        for _, (filename, code, _, _, frequency) in SERIES.items():
            url = f"https://www.eia.gov/dnav/pet/hist_xls/{code}{frequency}.xls"
            print("Descargando " + filename, flush=True)
            downloads.append(fetch(url, batch / filename))
        portal = batch / "portal_refinerias.html"
        downloads.append(fetch(REF_PORTAL, portal))
        href = linked_file(portal.read_text(encoding="utf-8"), r"refcap\d{2}\.xlsx$")
        filename = href.rsplit("/", 1)[-1]
        downloads.append(fetch(urljoin(REF_PORTAL, href), batch / filename))
        portal = batch / "portal_iwar.html"
        downloads.append(fetch(PORTAL_IWAR, portal))
        href = linked_file(portal.read_text(encoding="utf-8"), r"iwar-\d{8}\.txt$")
        stamp_date = re.search(r"(\d{8})\.txt$", href).group(1)
        downloads.append(fetch(urljoin(PORTAL_IWAR, href), batch / f"rrc_iwar_{stamp_date}.txt"))
        atomic_json(batch / "descargas.json", downloads)
    sources = convert(batch, downloads)
    atomic_json(manifest, {"version": 1, "fuentes": sources})
    print(f"Fuentes oficiales listas: {len(sources)}. La base existente no se ha modificado.")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actualizar", action="store_true", help="Descargar un lote nuevo conservando los anteriores")
    args = p.parse_args()
    try:
        update(args.actualizar)
    except Exception as exc:
        p.exit(1, f"ERROR: {exc}\nEl manifiesto anterior y la base se conservan.\n")

if __name__ == "__main__":
    main()
