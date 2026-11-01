"""Servidor local del programa de clientes de Carnicería Joaquin.

Solo usa la biblioteca estándar de Python y solo atiende a esta misma PC.
"""
import json
import os
import re
import sqlite3
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE =Path(__file__).resolve().parent
# El Python portátil de Windows no busca módulos junto al programa.
sys.path.insert(0, str(BASE))

import reglas

ESTATICOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/logo.jpg": ("logo.jpg", "image/jpeg"),
    "/vaca.png": ("vaca.png", "image/png"),
    "/cuenta-dni.png": ("cuenta-dni.png", "image/png"),
}
PUERTO = 8765
COPIAS_A_GUARDAR = 30
MONTO_MAXIMO = 100_000_000

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY,
    dni TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    cumple_mes INTEGER NOT NULL,
    cumple_dia INTEGER NOT NULL,
    telefono TEXT NOT NULL DEFAULT '',
    consentimiento TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visitas (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    fecha TEXT NOT NULL,
    monto INTEGER,
    descuento INTEGER NOT NULL DEFAULT 0,
    final INTEGER,
    anulada INTEGER NOT NULL DEFAULT 0,
    modificada TEXT
);
CREATE TABLE IF NOT EXISTS promos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL,
    activa INTEGER NOT NULL,
    beneficio TEXT NOT NULL,
    valor REAL NOT NULL DEFAULT 0,
    regalo TEXT NOT NULL DEFAULT '',
    piso INTEGER NOT NULL DEFAULT 0,
    techo INTEGER NOT NULL DEFAULT 0,
    desde TEXT,
    hasta TEXT,
    params TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS beneficios_usados (
    visita_id INTEGER NOT NULL REFERENCES visitas(id),
    promo_id INTEGER NOT NULL REFERENCES promos(id)
);
CREATE TABLE IF NOT EXISTS promos_generales (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    activa INTEGER NOT NULL,
    dias TEXT NOT NULL,
    desde TEXT,
    hasta TEXT,
    icono TEXT NOT NULL DEFAULT 'general'
);
"""

ICONOS_GENERALES = ("general", "vaca", "cuenta_dni")

# (tipo, activa, valor, nombre, params): valores iniciales del club, editables en la pestaña Promociones.
PROMOS_INICIALES = [
    ("visitas_semana", 1, 5, "Racha semanal: 2.ª visita", {"n": 2}),
    ("visitas_semana", 1, 10, "Racha semanal: 3.ª visita", {"n": 3}),
    ("racha_semanal", 1, 10, None, {}),
    ("cumpleanos", 1, 15, None, {}),
    ("cada_n_visitas", 0, 15, None, {}),
    ("dia_semana", 0, 5, None, {}),
    ("compra_grande", 0, 5, None, {}),
    ("bienvenida", 0, 5, None, {}),
    ("regreso", 0, 10, None, {}),
    ("cliente_historico", 0, 5, None, {}),
]

# Promociones del negocio para cualquier cliente: solo se informan, se cobran en la caja.
GENERALES_INICIALES = [
    ("Ganga Meat", "Llevando 2 kilos de cualquier corte vacuno, el kilo te sale a precio promocional.", [0, 1, 2, 3, 4, 5, 6], "vaca"),
    ("Cuenta DNI", "Pagá con Cuenta DNI y aprovechá el beneficio.", [0, 1, 2, 3, 4], "cuenta_dni"),
]


class ErrorDeUso(Exception):
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado


class Programa:
    def __init__(self, ruta_db, hoy=date.today):
        self.ruta_db = Path(ruta_db)
        self.hoy = hoy
        self.cerrojo = threading.Lock()
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.ruta_db, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(ESQUEMA)
        self._actualizar_base()
        if not self.db.execute("SELECT 1 FROM promos LIMIT 1").fetchone():
            for tipo, activa, valor, nombre, propios in PROMOS_INICIALES:
                m = reglas.MECANISMOS[tipo]
                params = {**{c["clave"]: c["defecto"] for c in m["campos"]}, **propios}
                piso = 50000 if tipo == "compra_grande" else 0
                self.db.execute(
                    "INSERT INTO promos (nombre, tipo, activa, beneficio, valor, piso, params) VALUES (?,?,?,?,?,?,?)",
                    (nombre or m["nombre"], tipo, activa, "porcentaje", valor, piso, json.dumps(params)),
                )
        if not self.db.execute("SELECT 1 FROM promos_generales LIMIT 1").fetchone():
            for nombre, descripcion, dias, icono in GENERALES_INICIALES:
                self.db.execute(
                    "INSERT INTO promos_generales (nombre, descripcion, activa, dias, icono) VALUES (?,?,1,?,?)",
                    (nombre, descripcion, json.dumps(dias), icono),
                )
        self.db.commit()
        self.copia_diaria()

    def _actualizar_base(self):
        """Suma a una base ya existente lo que agregaron las versiones nuevas."""
        columnas = {c["name"] for c in self.db.execute("PRAGMA table_info(promos_generales)")}
        if "icono" not in columnas:
            self.db.execute("ALTER TABLE promos_generales ADD COLUMN icono TEXT NOT NULL DEFAULT 'general'")
            for nombre, _, _, icono in GENERALES_INICIALES:
                self.db.execute("UPDATE promos_generales SET icono=? WHERE nombre=?", (icono, nombre))
        if "modificada" not in {c["name"] for c in self.db.execute("PRAGMA table_info(visitas)")}:
            self.db.execute("ALTER TABLE visitas ADD COLUMN modificada TEXT")
        self.db.execute("DROP INDEX IF EXISTS una_visita_por_dia")
        self.db.commit()

    def copia_diaria(self):
        carpeta = self.ruta_db.parent / "copias"
        carpeta.mkdir(exist_ok=True)
        destino = carpeta / f"carniceria-{self.hoy().isoformat()}.db"
        if destino.exists():
            return
        copia = sqlite3.connect(destino)
        with copia:
            self.db.backup(copia)
        copia.close()
        for vieja in sorted(carpeta.glob("carniceria-*.db"))[:-COPIAS_A_GUARDAR]:
            vieja.unlink()

    # Promos

    def promos(self):
        filas = self.db.execute("SELECT * FROM promos ORDER BY id").fetchall()
        return [{**dict(f), "activa": bool(f["activa"]), "params": json.loads(f["params"])} for f in filas]

    def promo_para_pantalla(self, promo):
        return {
            **promo,
            "mecanismo": reglas.MECANISMOS[promo["tipo"]]["nombre"],
            "descripcion": reglas.describir(promo),
        }

    def validar_promo(self, datos):
        tipo = datos.get("tipo")
        if tipo not in reglas.MECANISMOS:
            raise ErrorDeUso("Ese tipo de promoción no existe.")
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            raise ErrorDeUso("Falta el nombre de la promoción.")
        beneficio = datos.get("beneficio")
        if beneficio not in ("porcentaje", "monto", "regalo"):
            raise ErrorDeUso("Elegí qué se lleva el cliente.")
        valor = _numero(datos.get("valor", 0), "El valor del premio")
        regalo = str(datos.get("regalo", "")).strip()
        if beneficio == "porcentaje" and not 0 < valor <= 100:
            raise ErrorDeUso("El porcentaje tiene que estar entre 1 y 100.")
        if beneficio == "monto" and valor < 1:
            raise ErrorDeUso("Poné cuántos pesos se descuentan.")
        if beneficio == "regalo" and not regalo:
            raise ErrorDeUso("Escribí cuál es el regalo.")
        piso = int(_numero(datos.get("piso") or 0, "La compra mínima"))
        techo = int(_numero(datos.get("techo") or 0, "El descuento máximo"))
        desde, hasta = _fechas(datos)
        if tipo == "fechas" and not (desde and hasta):
            raise ErrorDeUso("Elegí las fechas desde y hasta.")
        if tipo == "compra_grande" and piso < 1:
            raise ErrorDeUso("Elegí desde qué monto de compra se gana.")
        params = self._validar_params(tipo, datos.get("params") or {})
        return (nombre, tipo, int(bool(datos.get("activa"))), beneficio, valor, regalo, piso, techo, desde, hasta, json.dumps(params))

    def _validar_params(self, tipo, recibidos):
        params = {}
        for campo in reglas.MECANISMOS[tipo]["campos"]:
            clave, valor = campo["clave"], recibidos.get(campo["clave"], campo["defecto"])
            if campo["tipo"] == "numero":
                minimo = campo.get("minimo", 1)
                valor = _numero(valor, campo["etiqueta"])
                if valor < minimo or valor != int(valor):
                    raise ErrorDeUso(f"Revisá el dato: {campo['etiqueta']}")
                params[clave] = int(valor)
            elif campo["tipo"] == "dias":
                if not isinstance(valor, list) or not valor or any(d not in range(7) for d in valor):
                    raise ErrorDeUso("Elegí al menos un día.")
                params[clave] = sorted(set(valor))
            else:
                params[clave] = bool(valor)
        return params

    def guardar_promo(self, datos, promo_id=None):
        fila = self.validar_promo(datos)
        columnas = "nombre=?, tipo=?, activa=?, beneficio=?, valor=?, regalo=?, piso=?, techo=?, desde=?, hasta=?, params=?"
        with self.db:
            if promo_id is None:
                cur = self.db.execute(
                    "INSERT INTO promos (nombre, tipo, activa, beneficio, valor, regalo, piso, techo, desde, hasta, params)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)", fila)
                promo_id = cur.lastrowid
            else:
                cur = self.db.execute(f"UPDATE promos SET {columnas} WHERE id=?", (*fila, promo_id))
                if not cur.rowcount:
                    raise ErrorDeUso("No encontramos esa promoción.", 404)
        return next(self.promo_para_pantalla(p) for p in self.promos() if p["id"] == promo_id)

    # Promociones para todos

    def generales(self):
        filas = self.db.execute("SELECT * FROM promos_generales ORDER BY id").fetchall()
        return [
            {**dict(f), "activa": bool(f["activa"]), "dias": json.loads(f["dias"]),
             "texto_dias": reglas.texto_dias(json.loads(f["dias"]))}
            for f in filas
        ]

    def guardar_general(self, datos, promo_id=None):
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            raise ErrorDeUso("Falta el nombre de la promoción.")
        dias = datos.get("dias")
        if not isinstance(dias, list) or not dias or any(d not in range(7) for d in dias):
            raise ErrorDeUso("Elegí al menos un día.")
        desde, hasta = _fechas(datos)
        icono = datos.get("icono", "general")
        if icono not in ICONOS_GENERALES:
            raise ErrorDeUso("Elegí un ícono de la lista.")
        fila = (nombre, str(datos.get("descripcion", "")).strip(), int(bool(datos.get("activa"))),
                json.dumps(sorted(set(dias))), desde, hasta, icono)
        with self.db:
            if promo_id is None:
                cur = self.db.execute(
                    "INSERT INTO promos_generales (nombre, descripcion, activa, dias, desde, hasta, icono) VALUES (?,?,?,?,?,?,?)", fila)
                promo_id = cur.lastrowid
            else:
                cur = self.db.execute(
                    "UPDATE promos_generales SET nombre=?, descripcion=?, activa=?, dias=?, desde=?, hasta=?, icono=? WHERE id=?",
                    (*fila, promo_id))
                if not cur.rowcount:
                    raise ErrorDeUso("No encontramos esa promoción.", 404)
        return next(p for p in self.generales() if p["id"] == promo_id)

    def borrar_general(self, promo_id):
        with self.db:
            cur = self.db.execute("DELETE FROM promos_generales WHERE id=?", (promo_id,))
        if not cur.rowcount:
            raise ErrorDeUso("No encontramos esa promoción.", 404)
        return {"ok": True}

    # Clientes

    def validar_cliente(self, datos):
        dni = re.sub(r"\D", "", str(datos.get("dni", "")))
        if not 7 <= len(dni) <= 8:
            raise ErrorDeUso("El DNI tiene que tener 7 u 8 números.")
        nombre = " ".join(str(datos.get("nombre", "")).split())
        if not nombre:
            raise ErrorDeUso("Falta el nombre.")
        try:
            mes, dia = int(datos.get("cumple_mes")), int(datos.get("cumple_dia"))
            date(2024, mes, dia)  # 2024 es bisiesto: acepta el 29 de febrero
        except (TypeError, ValueError):
            raise ErrorDeUso("Revisá el día y el mes del cumpleaños.")
        return dni, nombre, mes, dia, str(datos.get("telefono", "")).strip()

    def crear_cliente(self, datos):
        fila = self.validar_cliente(datos)
        if not datos.get("consentimiento"):
            raise ErrorDeUso("Falta que el cliente acepte que guardemos sus datos.")
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO clientes (dni, nombre, cumple_mes, cumple_dia, telefono, consentimiento) VALUES (?,?,?,?,?,?)",
                    (*fila, self.hoy().isoformat()))
        except sqlite3.IntegrityError:
            raise ErrorDeUso("Ya hay un cliente anotado con ese DNI.")
        return self.ficha_por_dni(fila[0])

    def editar_cliente(self, cliente_id, datos):
        dni, nombre, mes, dia, telefono = self.validar_cliente(datos)
        try:
            with self.db:
                cur = self.db.execute(
                    "UPDATE clientes SET dni=?, nombre=?, cumple_mes=?, cumple_dia=?, telefono=? WHERE id=?",
                    (dni, nombre, mes, dia, telefono, cliente_id))
        except sqlite3.IntegrityError:
            raise ErrorDeUso("Ya hay otro cliente con ese DNI.")
        if not cur.rowcount:
            raise ErrorDeUso("No encontramos ese cliente.", 404)
        return self.ficha_por_dni(dni)

    def _cliente(self, cliente_id):
        fila = self.db.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        if not fila:
            raise ErrorDeUso("No encontramos ese cliente.", 404)
        return fila

    def _historial(self, cliente):
        fechas = [date.fromisoformat(f["fecha"]) for f in self.db.execute(
            "SELECT fecha FROM visitas WHERE cliente_id=? AND anulada=0 ORDER BY fecha", (cliente["id"],))]
        usos = {}
        for fila in self.db.execute(
            "SELECT b.promo_id, v.fecha FROM beneficios_usados b JOIN visitas v ON v.id=b.visita_id"
            " WHERE v.cliente_id=? AND v.anulada=0", (cliente["id"],)):
            usos.setdefault(fila["promo_id"], []).append(date.fromisoformat(fila["fecha"]))
        return reglas.Historial(
            hoy=self.hoy(), fechas=fechas, usos=usos,
            cumple_mes=cliente["cumple_mes"], cumple_dia=cliente["cumple_dia"])

    def ficha_por_dni(self, dni):
        fila = self.db.execute("SELECT * FROM clientes WHERE dni=?", (re.sub(r"\D", "", dni),)).fetchone()
        if not fila:
            raise ErrorDeUso("No hay ningún cliente con ese DNI.", 404)
        return self.ficha(fila)

    def ficha(self, cliente):
        h, promos = self._historial(cliente), self.promos()
        hoy_tiene = reglas.candidatas(promos, h)
        visitas_hoy = self.db.execute(
            "SELECT id FROM visitas WHERE cliente_id=? AND fecha=? AND anulada=0 ORDER BY id DESC",
            (cliente["id"], self.hoy().isoformat())).fetchall()
        metas = [p["params"]["n"] for p in promos
                 if p["activa"] and p["tipo"] == "visitas_semana" and reglas.en_vigencia(p, self.hoy())]
        return {
            "cliente": dict(cliente),
            "racha": reglas.calcular_racha(h.fechas, h.hoy),
            "visitas_semana": reglas.visitas_de_la_semana(h.fechas, h.hoy),
            "meta_semana": max(metas) if metas else None,
            "total_visitas": len(h.fechas),
            "visitas_hoy": len(visitas_hoy),
            "ultima_visita_hoy_id": visitas_hoy[0]["id"] if visitas_hoy else None,
            "hoy_tiene": [self.promo_para_pantalla(p) for p in hoy_tiene],
            "proxima": reglas.proxima_promo(promos, h, excluir=hoy_tiene),
        }

    def clientes(self, texto="", estado="", limite=50):
        condicion, valores = _filtro_texto(texto)
        filas = self.db.execute(
            "SELECT c.id, c.dni, c.nombre, COUNT(v.id) AS visitas, MAX(v.fecha) AS ultima,"
            " COALESCE(SUM(v.final), 0) AS comprado"
            " FROM clientes c LEFT JOIN visitas v ON v.cliente_id = c.id AND v.anulada = 0"
            f" {'WHERE ' + condicion if condicion else ''} GROUP BY c.id"
            " ORDER BY ultima IS NULL, ultima DESC, c.nombre", valores).fetchall()
        hoy = self.hoy()
        lista = []
        for fila in filas:
            ultima = date.fromisoformat(fila["ultima"]) if fila["ultima"] else None
            lista.append({**dict(fila), "estado": reglas.estado_cliente(ultima, hoy)})
        if estado:
            lista = [c for c in lista if c["estado"]["clave"] == estado]
        return {"clientes": lista[:limite], "total": len(lista)}

    def perfil(self, dni):
        ficha = self.ficha_por_dni(dni)
        cliente_id, hoy = ficha["cliente"]["id"], self.hoy()
        fechas = self._historial(ficha["cliente"]).fechas
        ultima = max(fechas) if fechas else None
        cuentas = self.db.execute(
            "SELECT COALESCE(SUM(final), 0) AS comprado, COALESCE(SUM(descuento), 0) AS ahorrado,"
            " COUNT(monto) AS con_monto, AVG(monto) AS promedio"
            " FROM visitas WHERE cliente_id=? AND anulada=0", (cliente_id,)).fetchone()
        usados = self.db.execute(
            "SELECT p.nombre, COUNT(*) AS veces, MAX(v.fecha) AS ultima"
            " FROM beneficios_usados b JOIN visitas v ON v.id = b.visita_id JOIN promos p ON p.id = b.promo_id"
            " WHERE v.cliente_id=? AND v.anulada=0 GROUP BY p.id ORDER BY ultima DESC", (cliente_id,)).fetchall()
        return {
            **ficha,
            **self.movimientos(cliente_id=cliente_id, limite=10),
            "estado": reglas.estado_cliente(ultima, hoy),
            "primera_visita": min(fechas).isoformat() if fechas else None,
            "ultima_visita": ultima.isoformat() if ultima else None,
            "dias_sin_venir": (hoy - ultima).days if ultima else None,
            "dias_para_cumple": reglas.dias_para_cumple(
                ficha["cliente"]["cumple_mes"], ficha["cliente"]["cumple_dia"], hoy),
            "comprado": cuentas["comprado"],
            "ahorrado": cuentas["ahorrado"],
            "con_monto": cuentas["con_monto"],
            "promedio": round(cuentas["promedio"]) if cuentas["promedio"] else 0,
            "beneficios_usados": [dict(u) for u in usados],
        }

    # Visitas

    def _liquidacion(self, cliente, monto):
        h, promos = self._historial(cliente), self.promos()
        lista = reglas.candidatas(promos, h)
        if monto is not None and not 1 <= monto <= MONTO_MAXIMO:
            raise ErrorDeUso("Revisá el monto de la compra.")
        liq = reglas.liquidar(lista, monto)
        return h, promos, lista, liq

    def _liq_para_pantalla(self, liq):
        return {
            **liq,
            "promo": self.promo_para_pantalla(liq["promo"]) if liq["promo"] else None,
            "regalos": [{"nombre": p["nombre"], "regalo": p["regalo"]} for p in liq["regalos"]],
        }

    def vista_previa(self, datos):
        cliente = self._cliente(datos.get("cliente_id"))
        monto = _monto(datos.get("monto"))
        h, promos, lista, liq = self._liquidacion(cliente, monto)
        return {
            "candidatas": [self.promo_para_pantalla(p) for p in lista],
            "liquidacion": self._liq_para_pantalla(liq),
        }

    def registrar_visita(self, datos):
        cliente = self._cliente(datos.get("cliente_id"))
        monto = _monto(datos.get("monto"))
        h, promos, lista, liq = self._liquidacion(cliente, monto)
        if monto is None:
            raise ErrorDeUso("Falta poner el monto de la compra.")
        with self.db:
            cur = self.db.execute(
                "INSERT INTO visitas (cliente_id, fecha, monto, descuento, final) VALUES (?,?,?,?,?)",
                (cliente["id"], h.hoy.isoformat(), monto, liq["descuento"], liq["final"]))
            usadas = ([liq["promo"]] if liq["promo"] else []) + liq["regalos"]
            for promo in usadas:
                self.db.execute(
                    "INSERT INTO beneficios_usados (visita_id, promo_id) VALUES (?,?)", (cur.lastrowid, promo["id"]))
        self.copia_diaria()
        despues = self._historial(cliente)
        return {
            "visita_id": cur.lastrowid,
            "liquidacion": self._liq_para_pantalla(liq),
            "racha": reglas.calcular_racha(despues.fechas, despues.hoy),
            "proxima": reglas.proxima_promo(promos, despues),
        }

    def anular_visita(self, visita_id):
        with self.db:
            cur = self.db.execute("UPDATE visitas SET anulada=1 WHERE id=? AND anulada=0", (visita_id,))
        if not cur.rowcount:
            raise ErrorDeUso("Esa visita ya no se puede anular.", 404)
        return {"ok": True}

    # Movimientos

    def movimientos(self, texto="", desde=None, hasta=None, limite=50, cliente_id=None):
        desde, hasta = _fechas({"desde": desde, "hasta": hasta})
        condicion, valores = _filtro_texto(texto)
        condiciones = [condicion] if condicion else []
        if cliente_id is not None:
            condiciones.append("c.id = ?")
            valores.append(cliente_id)
        if desde:
            condiciones.append("v.fecha >= ?")
            valores.append(desde)
        if hasta:
            condiciones.append("v.fecha <= ?")
            valores.append(hasta)
        where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
        base = f"FROM visitas v JOIN clientes c ON c.id = v.cliente_id {where}"
        total = self.db.execute(f"SELECT COUNT(*) {base}", valores).fetchone()[0]
        filas = self.db.execute(
            f"SELECT v.*, c.nombre, c.dni {base} ORDER BY v.fecha DESC, v.id DESC LIMIT ?", (*valores, limite)).fetchall()
        resultado = [{**dict(f), "anulada": bool(f["anulada"]), "beneficios": []} for f in filas]
        por_id = {m["id"]: m for m in resultado}
        marcas = ",".join("?" * len(por_id))
        for fila in self.db.execute(
            f"SELECT b.visita_id, p.id, p.nombre FROM beneficios_usados b JOIN promos p ON p.id = b.promo_id"
            f" WHERE b.visita_id IN ({marcas})", list(por_id)):
            por_id[fila["visita_id"]]["beneficios"].append({"id": fila["id"], "nombre": fila["nombre"]})
        return {"movimientos": resultado, "total": total, "hoy": self.hoy().isoformat()}

    def _validar_movimiento(self, datos):
        dni = re.sub(r"\D", "", str(datos.get("dni", "")))
        cliente = self.db.execute("SELECT id FROM clientes WHERE dni=?", (dni,)).fetchone()
        if not cliente:
            raise ErrorDeUso("No hay ningún cliente con ese DNI. Si es nuevo, anotalo primero desde el inicio.")
        try:
            fecha = date.fromisoformat(str(datos.get("fecha")))
        except ValueError:
            raise ErrorDeUso("Elegí la fecha de la visita.")
        if fecha > self.hoy():
            raise ErrorDeUso("La fecha no puede ser futura.")
        monto = _monto(datos.get("monto"))
        if monto is not None and not 1 <= monto <= MONTO_MAXIMO:
            raise ErrorDeUso("Revisá el monto de la compra.")
        descuento = _monto(datos.get("descuento")) or 0
        if descuento < 0 or (monto is None and descuento) or (monto is not None and descuento > monto):
            raise ErrorDeUso("El descuento no puede ser mayor que la compra.")
        promo_ids = datos.get("promo_ids") or []
        conocidas = {p["id"] for p in self.promos()}
        if not isinstance(promo_ids, list) or any(i not in conocidas for i in promo_ids):
            raise ErrorDeUso("Revisá los beneficios elegidos.")
        final = None if monto is None else monto - descuento
        return (cliente["id"], fecha.isoformat(), monto, descuento, final), sorted(set(promo_ids))

    def guardar_movimiento(self, datos, visita_id=None):
        """Carga o corrige a mano: guarda lo que se indica, sin calcular premios."""
        fila, promo_ids = self._validar_movimiento(datos)
        hoy = self.hoy().isoformat()
        with self.db:
            if visita_id is None:
                cur = self.db.execute(
                    "INSERT INTO visitas (cliente_id, fecha, monto, descuento, final, modificada) VALUES (?,?,?,?,?,?)",
                    (*fila, hoy))
                visita_id = cur.lastrowid
            else:
                cur = self.db.execute(
                    "UPDATE visitas SET cliente_id=?, fecha=?, monto=?, descuento=?, final=?, modificada=? WHERE id=?",
                    (*fila, hoy, visita_id))
                if not cur.rowcount:
                    raise ErrorDeUso("No encontramos ese movimiento.", 404)
                self.db.execute("DELETE FROM beneficios_usados WHERE visita_id=?", (visita_id,))
            for promo_id in promo_ids:
                self.db.execute(
                    "INSERT INTO beneficios_usados (visita_id, promo_id) VALUES (?,?)", (visita_id, promo_id))
        self.copia_diaria()
        return {"id": visita_id}

    def recuperar_visita(self, visita_id):
        with self.db:
            cur = self.db.execute(
                "UPDATE visitas SET anulada=0, modificada=? WHERE id=? AND anulada=1", (self.hoy().isoformat(), visita_id))
        if not cur.rowcount:
            raise ErrorDeUso("Esa visita no está anulada.", 404)
        return {"ok": True}

    def inicio(self):
        hoy = self.hoy()
        promos = [p for p in self.promos() if reglas.vigente_hoy(p, hoy)]
        return {
            "hoy": hoy.isoformat(),
            "generales": [g for g in self.generales() if reglas.general_vigente(g, hoy)],
            "promos": [self.promo_para_pantalla(p) for p in promos],
        }

    def catalogo_promos(self):
        return {
            "generales": self.generales(),
            "promos": [self.promo_para_pantalla(p) for p in self.promos()],
            "mecanismos": reglas.MECANISMOS,
        }


def _numero(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorDeUso(f"Revisá el dato: {nombre}.")
    if numero < 0 or numero != numero or numero == float("inf"):
        raise ErrorDeUso(f"Revisá el dato: {nombre}.")
    return numero


def _filtro_texto(texto):
    texto = texto.strip()
    if not texto:
        return "", []
    return "(c.nombre LIKE ? OR c.dni LIKE ?)", [f"%{texto}%", f"%{re.sub(r'[^0-9]', '', texto) or texto}%"]


def _fechas(datos):
    desde, hasta = datos.get("desde") or None, datos.get("hasta") or None
    for texto in (desde, hasta):
        if texto:
            try:
                date.fromisoformat(texto)
            except (TypeError, ValueError):
                raise ErrorDeUso("Revisá las fechas de la promoción.")
    if desde and hasta and desde > hasta:
        raise ErrorDeUso("La fecha «desde» tiene que ser anterior a «hasta».")
    return desde, hasta


def _monto(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErrorDeUso("Revisá el monto de la compra.")
    return valor


def crear_manejador(programa, puerto):
    hosts = {f"127.0.0.1:{puerto}", f"localhost:{puerto}"}

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _responder(self, estado, cuerpo, tipo="application/json; charset=utf-8"):
            if not isinstance(cuerpo, bytes):
                cuerpo = json.dumps(cuerpo, ensure_ascii=False).encode()
            self.send_response(estado)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def _datos(self):
            # Pedir JSON evita que otra página web abierta en esta PC pueda escribir acá.
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                raise ErrorDeUso("Pedido inválido.", 415)
            largo = int(self.headers.get("Content-Length") or 0)
            try:
                datos = json.loads(self.rfile.read(largo) or b"{}")
            except ValueError:
                raise ErrorDeUso("Pedido inválido.")
            if not isinstance(datos, dict):
                raise ErrorDeUso("Pedido inválido.")
            return datos

        def _ruta(self, metodo):
            ruta = self.path.split("?", 1)[0]
            p = programa
            if metodo == "GET":
                if ruta == "/api/inicio":
                    return p.inicio()
                if ruta == "/api/promos":
                    return p.catalogo_promos()
                if ruta == "/api/movimientos":
                    q = parse_qs(urlsplit(self.path).query)
                    limite = q.get("limite", ["50"])[0]
                    return p.movimientos(
                        q.get("texto", [""])[0], q.get("desde", [None])[0], q.get("hasta", [None])[0],
                        min(int(limite), 2000) if limite.isdigit() else 50)
                if ruta == "/api/clientes":
                    q = parse_qs(urlsplit(self.path).query)
                    limite = q.get("limite", ["50"])[0]
                    return p.clientes(
                        q.get("texto", [""])[0], q.get("estado", [""])[0],
                        min(int(limite), 2000) if limite.isdigit() else 50)
                m = re.fullmatch(r"/api/clientes/(\d+)/perfil", ruta)
                if m:
                    return p.perfil(m[1])
                m = re.fullmatch(r"/api/clientes/(\d+)", ruta)
                if m:
                    return p.ficha_por_dni(m[1])
            elif metodo == "POST":
                if ruta == "/api/clientes":
                    return p.crear_cliente(self._datos())
                if ruta == "/api/visitas/vista-previa":
                    return p.vista_previa(self._datos())
                if ruta == "/api/visitas":
                    return p.registrar_visita(self._datos())
                if ruta == "/api/promos":
                    return p.guardar_promo(self._datos())
                if ruta == "/api/generales":
                    return p.guardar_general(self._datos())
                if ruta == "/api/movimientos":
                    return p.guardar_movimiento(self._datos())
                m = re.fullmatch(r"/api/visitas/(\d+)/anular", ruta)
                if m:
                    self._datos()
                    return p.anular_visita(int(m[1]))
                m = re.fullmatch(r"/api/visitas/(\d+)/recuperar", ruta)
                if m:
                    self._datos()
                    return p.recuperar_visita(int(m[1]))
            elif metodo == "PUT":
                m = re.fullmatch(r"/api/clientes/(\d+)", ruta)
                if m:
                    return p.editar_cliente(int(m[1]), self._datos())
                m = re.fullmatch(r"/api/promos/(\d+)", ruta)
                if m:
                    return p.guardar_promo(self._datos(), int(m[1]))
                m = re.fullmatch(r"/api/generales/(\d+)", ruta)
                if m:
                    return p.guardar_general(self._datos(), int(m[1]))
                m = re.fullmatch(r"/api/movimientos/(\d+)", ruta)
                if m:
                    return p.guardar_movimiento(self._datos(), int(m[1]))
            elif metodo == "DELETE":
                m = re.fullmatch(r"/api/generales/(\d+)", ruta)
                if m:
                    return p.borrar_general(int(m[1]))
            raise ErrorDeUso("No encontramos eso.", 404)

        def _atender(self, metodo):
            if self.headers.get("Host") not in hosts:
                return self._responder(403, {"error": "Solo se puede usar desde esta PC."})
            ruta = self.path.split("?", 1)[0]
            if metodo == "GET" and ruta in ESTATICOS:
                archivo, tipo = ESTATICOS[ruta]
                return self._responder(200, (BASE / "static" / archivo).read_bytes(), tipo)
            try:
                with programa.cerrojo:
                    self._responder(200, self._ruta(metodo))
            except ErrorDeUso as error:
                self._responder(error.estado, {"error": str(error)})
            except sqlite3.IntegrityError:
                self._responder(409, {"error": "No se pudo guardar. Revisá los datos."})

        def do_GET(self):
            self._atender("GET")

        def do_POST(self):
            self._atender("POST")

        def do_PUT(self):
            self._atender("PUT")

        def do_DELETE(self):
            self._atender("DELETE")

    return Manejador


class Servidor(ThreadingHTTPServer):
    # En Windows esta opción dejaría abrir dos programas en el mismo puerto.
    allow_reuse_address = os.name == "posix"


def puerto_libre(puerto):
    """Crea el servidor sin manejador, o None si el programa ya está abierto."""
    try:
        return Servidor(("127.0.0.1", puerto), BaseHTTPRequestHandler)
    except OSError:
        return None


def main():
    ruta_db = Path(os.environ.get("CARNICERIA_DB", BASE / "datos" / "carniceria.db"))
    if sys.stdout is None:  # sin ventana, los errores quedan en un archivo
        ruta_db.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(ruta_db.parent / "registro.log", "a", encoding="utf-8", buffering=1)
    puerto = int(os.environ.get("PUERTO", PUERTO))
    url = f"http://localhost:{puerto}/"
    abrir_navegador = not os.environ.get("SIN_NAVEGADOR")
    servidor = puerto_libre(puerto)
    if servidor is None:
        if abrir_navegador:
            webbrowser.open(url)
        return
    servidor.RequestHandlerClass = crear_manejador(Programa(ruta_db), puerto)
    print(f"Programa de clientes abierto en {url}")
    if abrir_navegador:
        webbrowser.open(url)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
