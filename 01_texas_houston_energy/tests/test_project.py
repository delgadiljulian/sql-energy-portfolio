"""Pruebas de regresión para los riesgos observados y la preservación de la base."""
import contextlib
import csv
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run as ejecutar
import build_database as build
from download_sources import sha

class RunnerTests(unittest.TestCase):
    def test_multisentencia_respeta_punto_y_coma_en_texto_y_comentarios(self):
        sql = "-- comentario;\nSELECT 'a;b'; /* otro; */ SELECT 2;"
        c = sqlite3.connect(":memory:")
        self.addCleanup(c.close)
        actual = [c.execute(s).fetchone() for s in ejecutar.statements(sql)]
        self.assertEqual(actual, [("a;b",), (2,)])

    def test_lectura_impide_ddl_y_attach(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "base.db"
            c = sqlite3.connect(p)
            c.execute("CREATE TABLE conservar(x)")
            c.commit()
            c.close()
            before = sha(p)
            c = ejecutar.connect_readonly(p)
            try:
                for sql in ["DROP TABLE conservar", "ATTACH DATABASE ':memory:' AS otra", "PRAGMA query_only=OFF"]:
                    with self.assertRaises(sqlite3.DatabaseError):
                        c.execute(sql)
            finally:
                c.close()
            self.assertEqual(before, sha(p))

    def test_exporta_mas_filas_que_la_vista_previa(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = sqlite3.connect(":memory:")
            c.execute("CREATE TABLE n(x)")
            c.executemany("INSERT INTO n VALUES (?)", [(i,) for i in range(71)])
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    ejecutar.run(c, "SELECT * FROM n ORDER BY x;", "resultado", 3, Path(tmp))
            finally:
                c.close()
            with (Path(tmp)/"resultado_01.csv").open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), 72)
            self.assertEqual(rows[-1], ["70"])

class IngestTests(unittest.TestCase):
    def connection(self):
        c = sqlite3.connect(":memory:")
        c.executescript((ROOT/"sql/schema.sql").read_text(encoding="utf-8"))
        c.execute("INSERT INTO fuentes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("test","test","observado_heredado","analitico",None,None,None,"registro","test.csv","a"*64,2,"{}"))
        self.addCleanup(c.close)
        return c

    def test_api_repetidos_se_conservan_y_conflictos_no_se_asignan(self):
        c = self.connection()
        headers = ["Operator Number","Operator Name","API County Number","API Unique Number","API",
                   "County Name","District Code","O/G Code","Lease Number","Well Number","Field Number","Field Name",
                   "API Depth","Shut In Date","Current Inactive Years","Current Inactive Months",
                   "Cost Calculation","Well Plugged","Original Completion Date"]
        base = ["1","OPERADOR A","3","12345","312345","Andrews","8A","O","123","1","77","CAMPO",
                "0","201801","2","9","100","N","19800101"]
        other = list(base)
        other[0],other[1],other[6],other[8] = "2","OPERADOR B","7B","456"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"test.csv"
            with p.open("w",encoding="utf-8",newline="") as f:
                w = csv.writer(f);w.writerow(headers);w.writerows([base,other])
            with patch.object(build,"ROOT",Path(tmp)):
                build.import_iwar(c,{"id":"test","archivo":"test.csv","filas":2})
        build.consolidate_iwar(c)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM pozos_inactivos_registros").fetchone()[0],2)
        self.assertEqual(c.execute("SELECT DISTINCT api FROM pozos_inactivos_registros").fetchall(),[("4200312345",)])
        self.assertEqual({r[0] for r in c.execute("SELECT distrito_rrc FROM pozos_inactivos_registros")},{"8A","7B"})
        self.assertEqual(c.execute("SELECT n_operadores,operador_id,n_distritos,distrito_rrc FROM vw_pozos_inactivos").fetchone(),
                         (2,None,2,None))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM pozos_inactivos_registros WHERE profundidad_pies IS NULL AND es_pozo_huerfano IS NULL").fetchone()[0],2)

    def test_no_confunde_ausencia_con_cero_y_admite_precio_negativo(self):
        self.assertIsNone(build.optional_number(""))
        self.assertEqual(build.optional_number("0"),0)
        c = self.connection()
        c.execute("INSERT INTO precios_observaciones VALUES ('test','WTI','2020-04-20',-36.98)")
        self.assertEqual(c.execute("SELECT precio_wti_usd,spread_brent_wti FROM precios_crudo_diario").fetchone(),(-36.98,None))

    def test_fecha_invalida_se_registra(self):
        c = self.connection()
        self.assertIsNone(build.optional_date(c,"test",2,"fecha","20200230"))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM incidencias_carga").fetchone()[0],1)

    def test_entero_fraccionario_no_se_trunca(self):
        with self.assertRaises(ValueError):
            build.integer("12.5")

class AtomicBuildTests(unittest.TestCase):
    def original(self,p):
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE original(x)")
        c.execute("INSERT INTO original VALUES (17)")
        c.commit();c.close()

    def test_validacion_fallida_conserva_base_y_limpia_temporal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"base.db"
            self.original(p)
            before=sha(p)
            with patch.object(build,"load_sources",return_value=[]), patch.object(build,"audit",side_effect=ValueError("fallo simulado")):
                with self.assertRaisesRegex(ValueError,"fallo simulado"):
                    build.build(p)
            self.assertEqual(before,sha(p))
            self.assertEqual(list(Path(tmp).glob(".build_*")),[])

    def test_sustitucion_y_respaldo_con_conexiones_cerradas(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"base.db"
            self.original(p)
            with patch.object(build,"load_sources",return_value=[]), patch.object(build,"audit",return_value={"controles":[],"tablas":{}}):
                report=build.build(p)
            with contextlib.closing(sqlite3.connect(p)) as c:
                self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0],2)
            with contextlib.closing(sqlite3.connect(report["respaldo"])) as c:
                self.assertEqual(c.execute("SELECT x FROM original").fetchone()[0],17)

    def test_cambio_concurrente_no_se_sobrescribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"base.db"
            self.original(p)
            def change(c,sources):
                with contextlib.closing(sqlite3.connect(p)) as external:
                    external.execute("UPDATE original SET x=99")
                    external.commit()
                return {"controles":[],"tablas":{}}
            with patch.object(build,"load_sources",return_value=[]),patch.object(build,"audit",side_effect=change):
                with self.assertRaisesRegex(ValueError,"cambió durante"):
                    build.build(p)
            with contextlib.closing(sqlite3.connect(p)) as c:
                self.assertEqual(c.execute("SELECT x FROM original").fetchone()[0],99)

if __name__=="__main__":
    unittest.main()
