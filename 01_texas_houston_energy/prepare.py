"""Punto único: fuentes verificadas y reconstrucción segura."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from download_sources import update
from build_database import build, ROOT

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actualizar", action="store_true", help="Descargar un nuevo lote oficial antes de reconstruir")
    args = p.parse_args()
    try:
        update(args.actualizar)
        result = build(reports=ROOT / "outputs")
        print(f"Listo: {len(result['controles'])} controles aprobados. Consulta outputs/VALIDACION.md.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
