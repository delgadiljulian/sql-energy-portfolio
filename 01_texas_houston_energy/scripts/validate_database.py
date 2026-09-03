"""Comprueba fuentes, cobertura e integridad sin modificar la base."""
import argparse
import sqlite3
from pathlib import Path
from contextlib import closing
from build_database import ROOT, DB, load_sources, audit, save_report, code_fingerprint

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base",type=Path,default=DB)
    p.add_argument("--guardar",action="store_true",help="Actualizar outputs/validacion.json y VALIDACION.md")
    args=p.parse_args()
    try:
        with closing(sqlite3.connect(args.base.resolve().as_uri()+"?mode=ro",uri=True)) as c:
            sources=load_sources()
            report=audit(c,sources)
            row=c.execute("SELECT carga_id,iniciado_utc,huella_codigo FROM ejecucion_carga").fetchone()
            report.update(dict(zip(["carga_id","iniciado_utc","huella_codigo"],row)))
            if report["huella_codigo"] != code_fingerprint():
                raise ValueError("La base fue construida con otra versión del modelo; ejecuta preparar.py")
        if args.guardar:
            save_report(report,ROOT/"outputs")
        print(f"Validación aprobada: {len(report['controles'])} controles. Base sin cambios.")
        for item in report["pozos_por_fuente"]:
            print(f"{item['fuente_id']}: {item['registros']:,} registros; {item['api_distintos']:,} API distintos.")
    except Exception as exc:
        p.exit(1,f"ERROR: {exc}\n")

if __name__=="__main__":
    main()
