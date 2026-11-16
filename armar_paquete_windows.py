"""Arma un .zip listo para la PC del negocio, con su propio Python portátil.

Se puede correr desde Linux. Descarga el Python oficial para Windows la primera vez.
Con --windows7 arma el paquete para Windows 7 SP1, con Python 3.8: el último que funciona ahí.
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
VERSION_PYTHON = "3.13.13"
VERSION_PYTHON_WINDOWS7 = "3.8.10"
CARPETA = "Club Carniceria Joaquin"

LEEME = """Club de clientes de Carniceria Joaquin

INSTALAR (una sola vez)
1. Extraer este .zip en una carpeta propia, por ejemplo C:\\Club Carniceria Joaquin.
   No usar "Archivos de programa": ahi Windows no deja guardar los datos.
2. Clic derecho en "Abrir Club de Clientes" > Enviar a > Escritorio (crear acceso directo).

USAR
Doble clic en el acceso directo del escritorio. Se abre en el navegador.
No hace falta cerrarlo. Si se cierra el navegador, otro doble clic lo vuelve a abrir.

COPIAS DE SEGURIDAD
Los datos estan en la carpeta "datos". Copiarla a un pendrive cada tanto.
Al actualizar el programa, conservar esa carpeta.
"""


def nombre_python(version):
    return f"python-{version}-embed-amd64.zip"


def bajar_python(version, destino):
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.python.org/ftp/python/{version}/{nombre_python(version)}"
    print(f"Descargando {url}")
    temporal = destino.with_suffix(".parcial")
    with urllib.request.urlopen(url) as respuesta, open(temporal, "wb") as archivo:
        while bloque := respuesta.read(1 << 16):
            archivo.write(bloque)
    temporal.replace(destino)


def armar(python_zip, salida):
    salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as paquete:
        for nombre in ("app.py", "reglas.py"):
            paquete.write(BASE / nombre, f"{CARPETA}/{nombre}")
        for archivo in sorted((BASE / "static").iterdir()):
            paquete.write(archivo, f"{CARPETA}/static/{archivo.name}")
        lanzador = (BASE / "iniciar.bat").read_text(encoding="ascii").replace("\n", "\r\n")
        paquete.writestr(f"{CARPETA}/Abrir Club de Clientes.bat", lanzador)
        paquete.writestr(f"{CARPETA}/LEEME.txt", LEEME.replace("\n", "\r\n"))
        with zipfile.ZipFile(python_zip) as python:
            nombres = python.namelist()
            if "pythonw.exe" not in nombres:
                raise SystemExit(f"{python_zip} no parece un Python para Windows.")
            for nombre in nombres:
                paquete.writestr(f"{CARPETA}/python/{nombre}", python.read(nombre))
    return salida


def main():
    windows7 = "--windows7" in sys.argv[1:]
    version = VERSION_PYTHON_WINDOWS7 if windows7 else VERSION_PYTHON
    python_zip = BASE / "dist" / "descargas" / nombre_python(version)
    bajar_python(version, python_zip)
    nombre = f"{CARPETA} (Windows 7).zip" if windows7 else f"{CARPETA}.zip"
    salida = armar(python_zip, BASE / "dist" / nombre)
    print(f"Listo: {salida} ({salida.stat().st_size // 1_000_000} MB)")


if __name__ == "__main__":
    sys.exit(main())
