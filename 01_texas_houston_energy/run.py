"""Ejecuta varias consultas; lectura por defecto y exportación CSV opcional."""
from __future__ import annotations
import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent
DB = (ROOT / "data/houston_energy.db") if (ROOT / "data/houston_energy.db").exists() else (ROOT / "data/houston_energy_v2.db")

def statements(sql):
    buffer = ""
    for char in sql:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    if buffer.strip():
        yield buffer

def connect_readonly(db):
    c = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only=ON")
    denied = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
              sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_TEMP_INDEX,
              sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
              sqlite3.SQLITE_CREATE_TEMP_VIEW, sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
              sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TEMP_INDEX,
              sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW,
              sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_ALTER_TABLE,
              sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_REINDEX,
              sqlite3.SQLITE_ANALYZE, sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE}
    read_pragmas = {"table_info", "table_xinfo", "index_list", "index_info", "foreign_key_list",
                    "foreign_key_check", "integrity_check", "quick_check", "database_list", "compile_options"}
    def authorize(action, arg1, arg2, dbname, trigger):
        if action in denied:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA and (arg1 or "").lower() not in read_pragmas:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    c.set_authorizer(authorize)
    return c

def show(headers, rows):
    values = [["NULL" if v is None else str(v) for v in row] for row in rows]
    widths = [min(55, max(len(h), max((len(r[i]) for r in values), default=0))) for i, h in enumerate(headers)]
    def line(row):
        return " | ".join((str(v)[:w-1] + "…" if len(str(v)) > w else str(v)).ljust(w) for v, w in zip(row, widths))
    print(line(headers))
    print("-+-".join("-"*w for w in widths))
    for row in values:
        print(line(row))

def run(c, sql, label, limit=30, csv_dir=None):
    result_index = 0
    for statement in statements(sql):
        started = perf_counter()
        cur = c.execute(statement)
        if cur.description is None:
            continue
        result_index += 1
        headers = [d[0] for d in cur.description]
        preview = cur.fetchmany(limit + 1)
        more = len(preview) > limit
        print(f"\n{label} · resultado {result_index}")
        show(headers, preview[:limit])
        if csv_dir:
            csv_dir.mkdir(parents=True, exist_ok=True)
            dest = csv_dir / f"{label}_{result_index:02d}.csv"
            total = len(preview)
            with dest.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(preview)
                while chunk := cur.fetchmany(1000):
                    writer.writerows(chunk)
                    total += len(chunk)
            print(f"{total} filas exportadas: {dest}")
        else:
            print(f"{'Primeras ' if more else ''}{min(len(preview),limit)} filas"
                  + ("; usa --csv para exportar el resultado completo." if more else "."))
        print(f"{(perf_counter()-started)*1000:.1f} ms")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("consulta", nargs="*", help="Archivo SQL o consulta entre comillas")
    p.add_argument("--todas", action="store_true", help="Ejecutar todas las guías")
    p.add_argument("--limite", type=int, default=30, help="Máximo de filas en pantalla")
    p.add_argument("--csv", type=Path, help="Carpeta de resultados completos")
    p.add_argument("--escritura", action="store_true", help="Permitir cambios explícitos a la base")
    p.add_argument("--base", type=Path, default=DB)
    args = p.parse_args()
    if not 1 <= args.limite <= 1000:
        p.error("--limite debe estar entre 1 y 1000")
    if args.todas and args.consulta:
        p.error("Usa una consulta o --todas")
    c = None
    try:
        if not args.base.is_file():
            raise FileNotFoundError("No existe la base. Ejecuta preparar.py.")
        if args.todas:
            jobs = [(f.stem, f.read_text(encoding="utf-8-sig")) for f in sorted((ROOT/"queries").glob("*.sql"))]
        elif args.consulta:
            text = " ".join(args.consulta)
            if "\n" not in text and len(text) < 240 and text.lower().endswith(".sql"):
                candidate = Path(text)
                if not candidate.is_file():
                    candidate = ROOT / text
                jobs = [(candidate.stem, candidate.read_text(encoding="utf-8-sig"))]
            else:
                jobs = [("consulta", text)]
        else:
            jobs = [("complete_queries_log", (ROOT/"queries/complete_queries_log.sql").read_text(encoding="utf-8-sig"))]
        c = sqlite3.connect(args.base) if args.escritura else connect_readonly(args.base)
        if args.escritura:
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("BEGIN")
        for label, sql in jobs:
            run(c, sql, label, args.limite, args.csv)
        if args.escritura:
            c.commit()
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        if c and args.escritura:
            c.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if c:
            c.close()

if __name__ == "__main__":
    sys.exit(main())
