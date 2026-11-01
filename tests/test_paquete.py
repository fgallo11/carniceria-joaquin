import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app
import armar_paquete_windows as armador


class Paquete(unittest.TestCase):
    def test_contiene_programa_python_y_lanzador(self):
        with tempfile.TemporaryDirectory() as carpeta:
            falso = Path(carpeta) / "python.zip"
            with zipfile.ZipFile(falso, "w") as z:
                z.writestr("pythonw.exe", "x")
            salida = armador.armar(falso, Path(carpeta) / "salida.zip")
            with zipfile.ZipFile(salida) as z:
                nombres = z.namelist()
                lanzador = z.read(f"{armador.CARPETA}/Abrir Club de Clientes.bat")
        for esperado in ("app.py", "reglas.py", "static/app.js", "static/index.html", "static/styles.css",
                         "python/pythonw.exe", "LEEME.txt"):
            self.assertIn(f"{armador.CARPETA}/{esperado}", nombres)
        self.assertIn(b"\r\n", lanzador)
        self.assertFalse([n for n in nombres if "/datos/" in n])

    def test_rechaza_un_zip_que_no_es_python(self):
        with tempfile.TemporaryDirectory() as carpeta:
            falso = Path(carpeta) / "otro.zip"
            with zipfile.ZipFile(falso, "w") as z:
                z.writestr("otra-cosa.txt", "x")
            with self.assertRaises(SystemExit):
                armador.armar(falso, Path(carpeta) / "salida.zip")


class SegundaApertura(unittest.TestCase):
    def test_si_ya_esta_abierto_no_crea_otro_servidor(self):
        primero = app.puerto_libre(0)
        try:
            self.assertIsNone(app.puerto_libre(primero.server_address[1]))
        finally:
            primero.server_close()


if __name__ == "__main__":
    unittest.main()
