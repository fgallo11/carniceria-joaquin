import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ErrorDeUso, Programa

CLIENTE = {"dni": "30.123.456", "nombre": "  María   Pérez ", "cumple_mes": 6, "cumple_dia": 15, "consentimiento": True}


class ProgramaBase(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.dia = date(2026, 11, 2)  # lunes
        self.p = Programa(Path(self.carpeta.name) / "prueba.db", hoy=lambda: self.dia)
        self.cliente = self.p.crear_cliente(CLIENTE)["cliente"]

    def tearDown(self):
        self.p.db.close()
        self.carpeta.cleanup()

    def visita(self, monto=10000):
        return self.p.registrar_visita({"cliente_id": self.cliente["id"], "monto": monto})

    def promo(self, tipo):
        return next(p for p in self.p.promos() if p["tipo"] == tipo)


class Clientes(ProgramaBase):
    def test_normaliza_datos(self):
        self.assertEqual(self.cliente["dni"], "30123456")
        self.assertEqual(self.cliente["nombre"], "María Pérez")

    def test_dni_repetido(self):
        with self.assertRaises(ErrorDeUso):
            self.p.crear_cliente(CLIENTE)

    def test_exige_consentimiento(self):
        with self.assertRaises(ErrorDeUso):
            self.p.crear_cliente({**CLIENTE, "dni": "20111222", "consentimiento": False})

    def test_cumple_invalido(self):
        with self.assertRaises(ErrorDeUso):
            self.p.crear_cliente({**CLIENTE, "dni": "20111222", "cumple_mes": 2, "cumple_dia": 30})

    def test_dni_desconocido(self):
        with self.assertRaises(ErrorDeUso) as e:
            self.p.ficha_por_dni("99999999")
        self.assertEqual(e.exception.estado, 404)


class Visitas(ProgramaBase):
    def test_toda_visita_exige_monto(self):
        with self.assertRaises(ErrorDeUso):
            self.visita(None)
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 0)

    def test_sin_promo_guarda_el_monto_e_informa_la_proxima(self):
        r = self.visita(7000)
        self.assertIsNone(r["liquidacion"]["promo"])
        self.assertEqual((r["liquidacion"]["monto"], r["liquidacion"]["final"]), (7000, 7000))
        self.assertEqual(self.p.movimientos()["movimientos"][0]["monto"], 7000)
        self.assertIn("falta 1 visita", r["proxima"]["frase"])
        self.assertIn("5%", r["proxima"]["beneficio"])

    def test_varias_visitas_el_mismo_dia_cuentan_para_la_racha_semanal(self):
        self.visita()
        ficha = self.p.ficha_por_dni("30123456")
        self.assertEqual((ficha["visitas_hoy"], ficha["visitas_semana"]), (1, 1))
        self.assertEqual(ficha["hoy_tiene"][0]["params"]["n"], 2)
        self.assertEqual(self.visita(20000)["liquidacion"]["descuento"], 1000)
        self.assertEqual(self.visita(20000)["liquidacion"]["descuento"], 2000)
        self.assertEqual(self.visita(20000)["liquidacion"]["descuento"], 0)
        ficha = self.p.ficha_por_dni("30123456")
        self.assertEqual((ficha["visitas_hoy"], ficha["total_visitas"], ficha["racha"]["semanas"]), (4, 4, 1))

    def test_anular_quita_solo_la_ultima_del_dia(self):
        self.visita()
        ultima = self.visita()["visita_id"]
        self.assertEqual(self.p.ficha_por_dni("30123456")["ultima_visita_hoy_id"], ultima)
        self.p.anular_visita(ultima)
        ficha = self.p.ficha_por_dni("30123456")
        self.assertEqual((ficha["visitas_hoy"], ficha["total_visitas"]), (1, 1))

    def test_base_anterior_pierde_el_limite_diario(self):
        self.p.db.execute(
            "CREATE UNIQUE INDEX una_visita_por_dia ON visitas(cliente_id, fecha) WHERE anulada = 0")
        self.p.db.commit()
        ruta = self.p.ruta_db
        self.p.db.close()
        self.p = Programa(ruta, hoy=lambda: self.dia)
        self.visita()
        self.visita()
        self.assertEqual(self.p.ficha_por_dni("30123456")["visitas_hoy"], 2)

    def test_racha_semanal_da_5_en_la_segunda_y_10_en_la_tercera(self):
        self.visita()
        self.dia += timedelta(days=1)
        previa = self.p.vista_previa({"cliente_id": self.cliente["id"]})
        self.assertEqual(previa["candidatas"][0]["params"]["n"], 2)
        self.assertEqual(self.visita(20000)["liquidacion"]["descuento"], 1000)
        self.dia += timedelta(days=1)
        r = self.visita(20000)
        self.assertEqual((r["liquidacion"]["descuento"], r["liquidacion"]["final"]), (2000, 18000))
        self.dia += timedelta(days=1)
        self.assertEqual(self.visita()["liquidacion"]["descuento"], 0)
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 4)

    def test_racha_acumulada_premia_a_las_cuatro_semanas(self):
        for _ in range(3):
            self.assertEqual(self.visita()["liquidacion"]["descuento"], 0)
            self.dia += timedelta(weeks=1)
        self.assertEqual(self.visita(10000)["liquidacion"]["descuento"], 1000)

    def test_vista_previa_no_guarda(self):
        self.p.vista_previa({"cliente_id": self.cliente["id"], "monto": 1000})
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 0)

    def test_anular_devuelve_la_visita_y_el_beneficio(self):
        self.dia = date(2026, 6, 15)
        r = self.visita(10000)
        self.assertEqual(r["liquidacion"]["descuento"], 1500)
        self.p.anular_visita(r["visita_id"])
        ficha = self.p.ficha_por_dni("30123456")
        self.assertEqual(ficha["total_visitas"], 0)
        self.assertTrue(ficha["hoy_tiene"])
        self.assertEqual(self.visita(10000)["liquidacion"]["descuento"], 1500)

    def test_cumple_no_se_repite_en_la_misma_ventana(self):
        self.dia = date(2026, 6, 15)
        self.visita(10000)
        self.dia += timedelta(days=1)
        r = self.visita(10000)["liquidacion"]
        self.assertEqual((r["promo"]["tipo"], r["descuento"]), ("visitas_semana", 500))

    def test_monto_invalido(self):
        for monto in (0, -5, 1.5, "100", True):
            with self.assertRaises(ErrorDeUso):
                self.p.vista_previa({"cliente_id": self.cliente["id"], "monto": monto})

    def test_copia_diaria(self):
        self.visita()
        self.assertTrue((Path(self.carpeta.name) / "copias" / "carniceria-2026-11-02.db").exists())


class Movimientos(ProgramaBase):
    def mov(self, **cambios):
        return {"dni": "30123456", "fecha": "2026-10-28", "monto": 10000, "descuento": 500, "promo_ids": [], **cambios}

    def lista(self, **filtros):
        return self.p.movimientos(**filtros)["movimientos"]

    def test_lista_lo_registrado_con_su_beneficio(self):
        self.visita()
        self.dia += timedelta(days=1)
        self.visita(20000)
        primero = self.lista()[0]
        self.assertEqual((primero["fecha"], primero["monto"], primero["descuento"], primero["final"]),
                         ("2026-11-03", 20000, 1000, 19000))
        self.assertEqual(primero["nombre"], "María Pérez")
        self.assertEqual(primero["beneficios"][0]["nombre"], "Racha semanal: 2.ª visita")
        self.assertEqual(self.lista()[1]["beneficios"], [])

    def test_cargar_visita_olvidada_suma_a_la_racha(self):
        self.visita()
        self.p.guardar_movimiento(self.mov())
        ficha = self.p.ficha_por_dni("30123456")
        self.assertEqual((ficha["total_visitas"], ficha["racha"]["semanas"]), (2, 2))
        m = next(x for x in self.lista() if x["fecha"] == "2026-10-28")
        self.assertEqual((m["final"], m["modificada"]), (9500, "2026-11-02"))

    def test_visita_olvidada_cambia_el_premio_siguiente(self):
        self.p.guardar_movimiento(self.mov(fecha="2026-11-02", monto=None, descuento=0))
        self.dia += timedelta(days=1)
        self.assertEqual(self.visita(10000)["liquidacion"]["descuento"], 500)

    def test_cambiar_fecha_recalcula_la_racha(self):
        self.visita()
        visita = self.p.guardar_movimiento(self.mov())["id"]
        self.p.guardar_movimiento(self.mov(fecha="2026-10-05"), visita)
        self.assertEqual(self.p.ficha_por_dni("30123456")["racha"]["semanas"], 1)

    def test_cambiar_monto_y_cliente(self):
        otro = self.p.crear_cliente({**CLIENTE, "dni": "20111222", "nombre": "Juan"})
        visita = self.visita()["visita_id"]
        self.p.guardar_movimiento(self.mov(dni="20111222", fecha="2026-11-02", monto=8000, descuento=0), visita)
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 0)
        self.assertEqual(self.p.ficha_por_dni("20111222")["total_visitas"], 1)
        self.assertEqual(self.lista()[0]["final"], 8000)
        self.assertEqual(otro["total_visitas"], 0)

    def test_marcar_beneficio_lo_cuenta_como_usado(self):
        cumple = self.promo("cumpleanos")
        visita = self.p.guardar_movimiento(self.mov(fecha="2026-11-02", promo_ids=[cumple["id"]]))["id"]
        self.assertEqual(self.lista()[0]["beneficios"][0]["id"], cumple["id"])
        self.dia = date(2027, 6, 15)
        tipos_de_hoy = lambda: [p["tipo"] for p in self.p.ficha_por_dni("30123456")["hoy_tiene"]]
        self.assertIn("cumpleanos", tipos_de_hoy())
        self.p.guardar_movimiento(self.mov(fecha="2027-06-14", promo_ids=[cumple["id"]]))
        self.assertNotIn("cumpleanos", tipos_de_hoy())
        self.p.guardar_movimiento(self.mov(fecha="2026-11-02", promo_ids=[]), visita)
        self.assertEqual(self.lista()[-1]["beneficios"], [])

    def test_validaciones(self):
        for malo in (
            {"fecha": "2026-11-03"}, {"fecha": ""}, {"dni": "11111111"}, {"monto": 0},
            {"descuento": 10001}, {"monto": None, "descuento": 100}, {"descuento": -1}, {"promo_ids": [999]},
        ):
            with self.assertRaises(ErrorDeUso, msg=malo):
                self.p.guardar_movimiento(self.mov(**malo))
        self.assertEqual(self.lista(), [])

    def test_permite_cargar_otra_visita_el_mismo_dia(self):
        self.visita()
        self.p.guardar_movimiento(self.mov(fecha="2026-11-02"))
        self.assertEqual(self.p.ficha_por_dni("30123456")["visitas_hoy"], 2)

    def test_error_al_cambiar_no_pierde_los_beneficios(self):
        promo = self.promo("cumpleanos")
        visita = self.p.guardar_movimiento(self.mov(promo_ids=[promo["id"]]))["id"]
        with self.assertRaises(ErrorDeUso):
            self.p.guardar_movimiento(self.mov(fecha="2099-01-01"), visita)
        m = next(x for x in self.lista() if x["id"] == visita)
        self.assertEqual((m["fecha"], len(m["beneficios"])), ("2026-10-28", 1))

    def test_anular_y_recuperar(self):
        visita = self.visita()["visita_id"]
        self.p.anular_visita(visita)
        self.assertTrue(self.lista()[0]["anulada"])
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 0)
        self.p.recuperar_visita(visita)
        self.assertEqual(self.p.ficha_por_dni("30123456")["total_visitas"], 1)

    def test_recupera_aunque_haya_otra_visita_ese_dia(self):
        visita = self.visita()["visita_id"]
        self.p.anular_visita(visita)
        self.visita()
        self.p.recuperar_visita(visita)
        self.assertEqual(self.p.ficha_por_dni("30123456")["visitas_hoy"], 2)

    def test_filtros(self):
        self.p.crear_cliente({**CLIENTE, "dni": "20111222", "nombre": "Juan Gómez"})
        self.p.guardar_movimiento(self.mov())
        self.p.guardar_movimiento(self.mov(dni="20111222", fecha="2026-10-10"))
        self.assertEqual(len(self.lista()), 2)
        self.assertEqual(self.lista(texto="gómez")[0]["dni"], "20111222")
        self.assertEqual(self.lista(texto="30.123.456")[0]["dni"], "30123456")
        self.assertEqual(len(self.lista(desde="2026-10-20")), 1)
        self.assertEqual(self.lista(hasta="2026-10-20")[0]["dni"], "20111222")
        self.assertEqual(self.p.movimientos(limite=1)["total"], 2)
        self.assertEqual(len(self.lista(limite=1)), 1)


class Perfil(ProgramaBase):
    def perfil(self):
        return self.p.perfil("30123456")

    def test_cliente_sin_visitas(self):
        p = self.perfil()
        self.assertEqual(p["estado"]["clave"], "sin_visitas")
        self.assertEqual((p["comprado"], p["ahorrado"], p["promedio"], p["ultima_visita"]), (0, 0, 0, None))
        self.assertEqual(p["cliente"]["cumple_dia"], 15)
        self.assertEqual(p["dias_para_cumple"], (date(2027, 6, 15) - self.dia).days)

    def test_suma_compras_descuentos_y_beneficios(self):
        self.visita(10000)
        self.visita(20000)
        p = self.perfil()
        self.assertEqual((p["comprado"], p["ahorrado"], p["promedio"]), (29000, 1000, 15000))
        self.assertEqual((p["primera_visita"], p["ultima_visita"], p["dias_sin_venir"]), ("2026-11-02", "2026-11-02", 0))
        self.assertEqual([u["nombre"] for u in p["beneficios_usados"]], ["Racha semanal: 2.ª visita"])
        self.assertEqual(len(p["movimientos"]), 2)

    def test_las_anuladas_no_suman_pero_se_listan(self):
        visita = self.visita(10000)["visita_id"]
        self.p.anular_visita(visita)
        p = self.perfil()
        self.assertEqual((p["comprado"], p["total_visitas"], p["estado"]["clave"]), (0, 0, "sin_visitas"))
        self.assertTrue(p["movimientos"][0]["anulada"])

    def test_estado_cambia_con_el_tiempo(self):
        self.visita()
        self.assertEqual(self.perfil()["estado"]["clave"], "activo")
        self.dia += timedelta(weeks=1)
        self.assertEqual(self.perfil()["estado"]["clave"], "activo")
        self.dia += timedelta(weeks=1)
        self.assertEqual(self.perfil()["estado"]["clave"], "en_riesgo")
        self.dia += timedelta(weeks=1)
        self.assertEqual(self.perfil()["estado"]["clave"], "inactivo")

    def test_movimientos_solo_de_ese_cliente(self):
        self.p.crear_cliente({**CLIENTE, "dni": "1301234560"[:8], "nombre": "Otro"})
        self.visita()
        self.assertEqual({m["dni"] for m in self.perfil()["movimientos"]}, {"30123456"})

    def test_dni_desconocido(self):
        with self.assertRaises(ErrorDeUso):
            self.p.perfil("99999999")

    def test_lista_y_filtros(self):
        self.p.crear_cliente({**CLIENTE, "dni": "20111222", "nombre": "Juan Gómez"})
        self.visita(5000)
        lista = self.p.clientes()
        self.assertEqual([c["dni"] for c in lista["clientes"]], ["30123456", "20111222"])
        self.assertEqual((lista["clientes"][0]["visitas"], lista["clientes"][0]["comprado"]), (1, 5000))
        self.assertEqual(self.p.clientes(texto="gómez")["clientes"][0]["dni"], "20111222")
        self.assertEqual(self.p.clientes(texto="30.123")["total"], 1)
        self.assertEqual(self.p.clientes(estado="sin_visitas")["clientes"][0]["dni"], "20111222")
        self.assertEqual(self.p.clientes(estado="inactivo")["total"], 0)
        recortada = self.p.clientes(limite=1)
        self.assertEqual((len(recortada["clientes"]), recortada["total"]), (1, 2))

    def test_cumple_cae_hoy(self):
        self.dia = date(2026, 6, 15)
        self.assertEqual(self.perfil()["dias_para_cumple"], 0)


class Generales(ProgramaBase):
    def nombres_hoy(self):
        return [g["nombre"] for g in self.p.inicio()["generales"]]

    def test_cuenta_dni_solo_de_lunes_a_viernes(self):
        self.assertEqual(self.nombres_hoy(), ["Ganga Meat", "Cuenta DNI"])
        self.dia = date(2026, 11, 7)  # sábado
        self.assertEqual(self.nombres_hoy(), ["Ganga Meat"])

    def test_no_se_mezclan_con_las_del_club(self):
        self.assertFalse([p for p in self.p.inicio()["promos"] if p["nombre"] == "Ganga Meat"])

    def test_apagar_fechas_y_borrar(self):
        ganga = self.p.generales()[0]
        self.p.guardar_general({**ganga, "activa": False}, ganga["id"])
        self.assertEqual(self.nombres_hoy(), ["Cuenta DNI"])
        self.p.guardar_general({**ganga, "activa": True, "hasta": "2026-11-01"}, ganga["id"])
        self.assertEqual(self.nombres_hoy(), ["Cuenta DNI"])
        self.p.borrar_general(ganga["id"])
        self.assertEqual(len(self.p.generales()), 1)

    def test_crear_y_validar(self):
        nueva = self.p.guardar_general({"nombre": "Asado", "descripcion": "x", "activa": True, "dias": [0, 5]})
        self.assertEqual(nueva["texto_dias"], "Lunes y sábado")
        for mala in ({"nombre": " ", "dias": [0]}, {"nombre": "a", "dias": []}, {"nombre": "a", "dias": [9]},
                     {"nombre": "a", "dias": [0], "desde": "2026-12-01", "hasta": "2026-11-01"}):
            with self.assertRaises(ErrorDeUso, msg=mala):
                self.p.guardar_general(mala)

    def test_iconos(self):
        iconos = {g["nombre"]: g["icono"] for g in self.p.generales()}
        self.assertEqual(iconos, {"Ganga Meat": "vaca", "Cuenta DNI": "cuenta_dni"})
        with self.assertRaises(ErrorDeUso):
            self.p.guardar_general({"nombre": "a", "dias": [0], "icono": "otro"})

    def test_base_anterior_recibe_los_iconos(self):
        ruta = self.p.ruta_db
        self.p.db.execute("ALTER TABLE promos_generales DROP COLUMN icono")
        self.p.db.commit()
        self.p.db.close()
        self.p = Programa(ruta, hoy=lambda: self.dia)
        iconos = {g["nombre"]: g["icono"] for g in self.p.generales()}
        self.assertEqual(iconos, {"Ganga Meat": "vaca", "Cuenta DNI": "cuenta_dni"})

    def test_texto_de_dias(self):
        textos = {g["nombre"]: g["texto_dias"] for g in self.p.generales()}
        self.assertEqual(textos, {"Ganga Meat": "Todos los días", "Cuenta DNI": "De lunes a viernes"})


class Promos(ProgramaBase):
    def guardar(self, promo, **cambios):
        return self.p.guardar_promo({**promo, **cambios}, promo["id"])

    def test_apagar_promo_saca_el_beneficio_y_la_pizarra(self):
        for promo in self.p.promos():
            if promo["tipo"] == "visitas_semana":
                self.guardar(promo, activa=False)
        nombres = [p["tipo"] for p in self.p.inicio()["promos"]]
        self.assertNotIn("visitas_semana", nombres)
        self.assertNotEqual(self.visita()["proxima"], None)

    def test_techo_y_piso_se_aplican(self):
        self.guardar(self.promo("cumpleanos"), valor=50, techo=1000, piso=5000)
        self.dia = date(2026, 6, 15)
        previa = self.p.vista_previa({"cliente_id": self.cliente["id"], "monto": 3000})["liquidacion"]
        self.assertEqual(previa["no_llegan"][0]["faltan"], 2000)
        previa = self.p.vista_previa({"cliente_id": self.cliente["id"], "monto": 8000})["liquidacion"]
        self.assertEqual(previa["descuento"], 1000)

    def test_validaciones(self):
        base = self.promo("visitas_semana")
        for cambios in (
            {"valor": 0}, {"valor": 101}, {"nombre": " "}, {"tipo": "otro"},
            {"beneficio": "regalo", "regalo": ""}, {"params": {"n": 0}},
            {"desde": "2026-12-01", "hasta": "2026-11-01"},
        ):
            with self.assertRaises(ErrorDeUso, msg=cambios):
                self.guardar(base, **cambios)

    def test_fechas_exige_rango(self):
        with self.assertRaises(ErrorDeUso):
            self.p.guardar_promo({
                "nombre": "Fiestas", "tipo": "fechas", "beneficio": "porcentaje", "valor": 10, "activa": True})

    def test_crear_promo_nueva(self):
        nueva = self.p.guardar_promo({
            "nombre": "Martes", "tipo": "dia_semana", "beneficio": "regalo", "regalo": "Chimichurri",
            "activa": True, "params": {"dias": [1]}})
        self.assertIn("martes", nueva["descripcion"])


if __name__ == "__main__":
    unittest.main()
