"""Abre el paquete en un Windows real, como lo haría un doble clic, y usa el programa.

No lo corre `unittest`: lo corre GitHub Actions con el .zip ya armado.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "http://localhost:8765"


def pedir(ruta, datos=None):
    cuerpo = None if datos is None else json.dumps(datos).encode()
    pedido = urllib.request.Request(URL + ruta, cuerpo, {"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=5) as respuesta:
        return respuesta.read()


def pedir_json(ruta, datos=None):
    return json.loads(pedir(ruta, datos))


def esperar_programa():
    for _ in range(60):
        try:
            return pedir_json("/api/inicio")
        except OSError:
            time.sleep(1)
    raise SystemExit("El programa no arrancó en 60 segundos.")


def rutas_de_pythonw():
    salida = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "(Get-Process pythonw -ErrorAction SilentlyContinue).Path"],
        capture_output=True, text=True, check=True).stdout
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def abrir(lanzador, entorno):
    subprocess.run([str(lanzador)], cwd=lanzador.parent, env=entorno, check=True, timeout=30)


def probar(carpeta):
    lanzador = carpeta / "Abrir Club de Clientes.bat"
    entorno = {**os.environ, "SIN_NAVEGADOR": "1"}
    abrir(lanzador, entorno)

    inicio = esperar_programa()
    assert [g["nombre"] for g in inicio["generales"]], "Faltan las promociones para todos"
    assert b"Club" in pedir("/"), "No se sirve la página"
    for archivo in ("/app.js", "/styles.css", "/logo.jpg", "/vaca.png", "/cuenta-dni.png"):
        assert pedir(archivo), f"Falta {archivo}"

    cliente = pedir_json("/api/clientes", {
        "dni": "30123456", "nombre": "María Pérez", "cumple_mes": 6, "cumple_dia": 15, "consentimiento": True,
    })["cliente"]
    pedir_json("/api/visitas", {"cliente_id": cliente["id"], "monto": 10000})
    segunda = pedir_json("/api/visitas", {"cliente_id": cliente["id"], "monto": 20000})
    assert segunda["liquidacion"]["descuento"] == 1000, segunda
    perfil = pedir_json("/api/clientes/30123456/perfil")
    assert (perfil["total_visitas"], perfil["comprado"]) == (2, 29000), perfil

    abrir(lanzador, entorno)
    time.sleep(5)
    rutas = rutas_de_pythonw()
    assert len(rutas) == 1, f"Tiene que haber un solo programa abierto: {rutas}"
    assert Path(rutas[0]).resolve().parent == (carpeta / "python").resolve(), f"No usa el Python del paquete: {rutas}"
    assert pedir_json("/api/clientes/30123456")["total_visitas"] == 2, "Se perdieron datos al abrirlo de nuevo"

    assert (carpeta / "datos" / "carniceria.db").exists(), "No se guardó la base"
    assert list((carpeta / "datos" / "copias").glob("carniceria-*.db")), "No se hizo la copia de seguridad"
    registro = (carpeta / "datos" / "registro.log").read_text(encoding="utf-8")
    assert "Traceback" not in registro, registro


def main():
    temporal = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(sys.argv[1]) as paquete:
        paquete.extractall(temporal)
    carpeta = next(temporal.iterdir())
    try:
        probar(carpeta)
        print("El paquete abre y funciona en Windows.")
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"], capture_output=True)
        shutil.rmtree(temporal, ignore_errors=True)


if __name__ == "__main__":
    main()
