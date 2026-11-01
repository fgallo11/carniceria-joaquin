import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reglas
from reglas import Historial

MIERCOLES = date(2026, 11, 4)


def promo(tipo, id=1, activa=True, beneficio="porcentaje", valor=10, piso=0, techo=0, desde=None, hasta=None, **params):
    return {
        "id": id, "nombre": tipo, "tipo": tipo, "activa": activa, "beneficio": beneficio,
        "valor": valor, "regalo": "Chimichurri", "piso": piso, "techo": techo,
        "desde": desde, "hasta": hasta, "params": params,
    }


def semanas_atras(n, dia=MIERCOLES):
    return dia - timedelta(weeks=n)


class Racha(unittest.TestCase):
    def test_sin_visitas(self):
        self.assertEqual(reglas.calcular_racha([], MIERCOLES)["semanas"], 0)

    def test_varias_visitas_en_una_semana_suman_una(self):
        fechas = [MIERCOLES, MIERCOLES - timedelta(days=1)]
        self.assertEqual(reglas.calcular_racha(fechas, MIERCOLES)["semanas"], 1)

    def test_semanas_seguidas(self):
        fechas = [semanas_atras(i) for i in range(3)]
        self.assertEqual(reglas.calcular_racha(fechas, MIERCOLES)["semanas"], 3)

    def test_una_semana_sin_venir_se_perdona_sin_sumar(self):
        fechas = [semanas_atras(2), MIERCOLES]
        self.assertEqual(reglas.calcular_racha(fechas, MIERCOLES)["semanas"], 2)

    def test_dos_semanas_seguidas_sin_venir_cortan(self):
        fechas = [semanas_atras(3), MIERCOLES]
        self.assertEqual(reglas.calcular_racha(fechas, MIERCOLES)["semanas"], 1)

    def test_avisa_riesgo_durante_la_semana_perdonada(self):
        racha = reglas.calcular_racha([semanas_atras(2)], MIERCOLES)
        self.assertEqual(racha, {"semanas": 1, "en_riesgo": True})

    def test_la_racha_vence_sin_nueva_visita(self):
        self.assertEqual(reglas.calcular_racha([semanas_atras(3)], MIERCOLES)["semanas"], 0)


class Candidatas(unittest.TestCase):
    def gana(self, p, **kw):
        return bool(reglas.candidatas([p], Historial(hoy=kw.pop("hoy", MIERCOLES), **kw)))

    def test_tercera_visita_de_la_semana(self):
        p = promo("visitas_semana", n=3)
        lunes, martes = date(2026, 11, 2), date(2026, 11, 3)
        self.assertFalse(self.gana(p, fechas=[lunes]))
        self.assertTrue(self.gana(p, fechas=[lunes, martes]))

    def test_visitas_del_mismo_dia_cuentan_por_separado(self):
        p = promo("visitas_semana", n=3)
        self.assertTrue(self.gana(p, fechas=[MIERCOLES, MIERCOLES]))
        self.assertFalse(self.gana(p, fechas=[MIERCOLES]))
        self.assertTrue(self.gana(promo("cada_n_visitas", n=2), fechas=[MIERCOLES]))

    def test_racha_de_semanas_no_se_repite_en_el_mismo_dia(self):
        p = promo("racha_semanal", n=1)
        self.assertFalse(self.gana(p, fechas=[MIERCOLES]))

    def test_cuarta_visita_ya_no_gana(self):
        p = promo("visitas_semana", n=3)
        fechas = [date(2026, 11, d) for d in (2, 3, 4)]
        self.assertFalse(self.gana(p, fechas=fechas, hoy=date(2026, 11, 5)))

    def test_promo_apagada_o_fuera_de_vigencia(self):
        self.assertFalse(self.gana(promo("bienvenida", activa=False)))
        self.assertFalse(self.gana(promo("bienvenida", hasta="2026-11-03")))
        self.assertFalse(self.gana(promo("bienvenida", desde="2026-11-05")))

    def test_cumple_dentro_de_la_ventana(self):
        p = promo("cumpleanos", dias_antes=3, dias_despues=3)
        self.assertTrue(self.gana(p, cumple_mes=11, cumple_dia=7))
        self.assertTrue(self.gana(p, cumple_mes=11, cumple_dia=1))
        self.assertFalse(self.gana(p, cumple_mes=11, cumple_dia=8))

    def test_cumple_solo_una_vez(self):
        p = promo("cumpleanos", dias_antes=3, dias_despues=3)
        usos = {1: [date(2026, 11, 3)]}
        self.assertFalse(self.gana(p, cumple_mes=11, cumple_dia=4, usos=usos))

    def test_cumple_cruza_el_anio(self):
        p = promo("cumpleanos", dias_antes=3, dias_despues=3)
        self.assertTrue(self.gana(p, hoy=date(2027, 1, 1), cumple_mes=12, cumple_dia=30))

    def test_cumple_29_de_febrero_en_anio_comun(self):
        p = promo("cumpleanos", dias_antes=0, dias_despues=0)
        self.assertTrue(self.gana(p, hoy=date(2027, 2, 28), cumple_mes=2, cumple_dia=29))

    def test_dia_de_la_semana(self):
        self.assertTrue(self.gana(promo("dia_semana", dias=[2])))
        self.assertFalse(self.gana(promo("dia_semana", dias=[1])))

    def test_sellos_cada_n_visitas(self):
        p = promo("cada_n_visitas", n=3)
        fechas = [MIERCOLES - timedelta(days=d) for d in (1, 2)]
        self.assertTrue(self.gana(p, fechas=fechas))
        self.assertFalse(self.gana(p, fechas=fechas[:1]))

    def test_racha_de_semanas_solo_en_la_primera_visita_semanal(self):
        p = promo("racha_semanal", n=2)
        self.assertTrue(self.gana(p, fechas=[semanas_atras(1)]))
        self.assertFalse(self.gana(p, fechas=[semanas_atras(1), MIERCOLES - timedelta(days=1)]))

    def test_regreso(self):
        p = promo("regreso", n=4)
        self.assertTrue(self.gana(p, fechas=[semanas_atras(5)]))
        self.assertFalse(self.gana(p, fechas=[semanas_atras(4)]))

    def test_bienvenida_solo_la_primera_vez(self):
        self.assertTrue(self.gana(promo("bienvenida")))
        self.assertFalse(self.gana(promo("bienvenida"), fechas=[semanas_atras(1)]))

    def test_fecha_especial_una_vez_por_cliente(self):
        p = promo("fechas", desde="2026-11-01", hasta="2026-11-30", una_vez=True)
        self.assertTrue(self.gana(p))
        self.assertFalse(self.gana(p, usos={1: [date(2026, 11, 2)]}))

    def test_cliente_historico(self):
        p = promo("cliente_historico", n=2)
        self.assertTrue(self.gana(p, fechas=[semanas_atras(9)]))
        self.assertFalse(self.gana(p))


class Liquidacion(unittest.TestCase):
    def test_porcentaje(self):
        r = reglas.liquidar([promo("bienvenida", valor=10)], 12345)
        self.assertEqual((r["descuento"], r["final"]), (1235, 11110))

    def test_techo_limita_el_descuento(self):
        r = reglas.liquidar([promo("bienvenida", valor=50, techo=1000)], 10000)
        self.assertEqual((r["descuento"], r["final"]), (1000, 9000))

    def test_piso_no_alcanzado_avisa_cuanto_falta(self):
        r = reglas.liquidar([promo("bienvenida", piso=5000)], 3000)
        self.assertEqual(r["descuento"], 0)
        self.assertIsNone(r["promo"])
        self.assertEqual(r["no_llegan"][0]["faltan"], 2000)

    def test_piso_justo_alcanza(self):
        r = reglas.liquidar([promo("bienvenida", piso=5000)], 5000)
        self.assertEqual(r["descuento"], 500)

    def test_monto_fijo_no_supera_la_compra(self):
        r = reglas.liquidar([promo("bienvenida", beneficio="monto", valor=2000)], 1500)
        self.assertEqual((r["descuento"], r["final"]), (1500, 0))

    def test_no_se_acumulan_gana_el_mayor(self):
        lista = [promo("bienvenida", id=1, valor=10), promo("bienvenida", id=2, valor=20)]
        r = reglas.liquidar(lista, 1000)
        self.assertEqual((r["promo"]["id"], r["descuento"]), (2, 200))

    def test_regalo_va_junto_con_el_descuento(self):
        lista = [promo("bienvenida", id=1), promo("bienvenida", id=2, beneficio="regalo")]
        r = reglas.liquidar(lista, 1000)
        self.assertEqual(r["descuento"], 100)
        self.assertEqual(len(r["regalos"]), 1)

    def test_vista_sin_monto_no_calcula_descuento(self):
        r = reglas.liquidar([promo("bienvenida")], None)
        self.assertEqual((r["descuento"], r["final"], r["promo"]), (0, None, None))


class Proxima(unittest.TestCase):
    def test_elige_la_mas_cercana(self):
        promos = [promo("cada_n_visitas", id=1, n=10), promo("visitas_semana", id=2, n=3)]
        h = Historial(hoy=MIERCOLES, fechas=[MIERCOLES])
        p = reglas.proxima_promo(promos, h)
        self.assertEqual(p["nombre"], "visitas_semana")
        self.assertIn("faltan 2 visitas", p["frase"])

    def test_si_no_llega_en_la_semana_propone_la_siguiente(self):
        domingo = date(2026, 11, 8)
        h = Historial(hoy=domingo, fechas=[domingo])
        p = reglas.proxima_promo([promo("visitas_semana", n=3)], h)
        self.assertIn("en una misma semana", p["frase"])
        self.assertEqual(p["dias"], 3)

    def test_sin_promos_activas(self):
        h = Historial(hoy=MIERCOLES)
        self.assertIsNone(reglas.proxima_promo([promo("visitas_semana", activa=False, n=3)], h))

    def test_descarta_lo_que_vence_antes(self):
        h = Historial(hoy=MIERCOLES, fechas=[MIERCOLES])
        p = promo("cada_n_visitas", n=10, hasta="2026-11-06")
        self.assertIsNone(reglas.proxima_promo([p], h))

    def test_excluye_lo_que_ya_gana_hoy(self):
        h = Historial(hoy=MIERCOLES)
        p = promo("compra_grande", piso=1000)
        self.assertIsNone(reglas.proxima_promo([p], h, excluir=[p]))

    def test_mecanismos_sin_camino_no_se_proponen(self):
        h = Historial(hoy=MIERCOLES, fechas=[MIERCOLES])
        self.assertIsNone(reglas.proxima_promo([promo("bienvenida"), promo("regreso", id=2, n=4)], h))


class Textos(unittest.TestCase):
    def test_cada_mecanismo_tiene_descripcion(self):
        for tipo, datos in reglas.MECANISMOS.items():
            params = {c["clave"]: c["defecto"] for c in datos["campos"]}
            self.assertTrue(reglas.describir(promo(tipo, **params)))

    def test_condiciones_visibles(self):
        texto = reglas.describir(promo("bienvenida", piso=5000, techo=2000))
        self.assertIn("desde $5.000", texto)
        self.assertIn("descuento máximo $2.000", texto)


if __name__ == "__main__":
    unittest.main()
