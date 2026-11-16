"""Reglas del programa: rachas, promociones y cálculo de descuentos.

No toca la base de datos ni la red, para poder probarlo con fechas fijas.
Los montos son pesos enteros. La semana va de lunes a domingo.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

MECANISMOS = {
    "visitas_semana": {
        "nombre": "Racha semanal",
        "ayuda": "Premia una visita puntual dentro de la misma semana, como la segunda o la tercera.",
        "campos": [{"clave": "n", "etiqueta": "¿En qué visita de la semana se gana?", "tipo": "numero", "defecto": 3}],
    },
    "racha_semanal": {
        "nombre": "Racha acumulada",
        "ayuda": "Premia a quien viene semana tras semana. Se perdona una semana sin venir.",
        "campos": [{"clave": "n", "etiqueta": "¿Cada cuántas semanas de racha se gana?", "tipo": "numero", "defecto": 4}],
    },
    "cada_n_visitas": {
        "nombre": "Tarjeta de sellos",
        "ayuda": "Cada cierta cantidad de visitas, sin importar cuándo fueron.",
        "campos": [{"clave": "n", "etiqueta": "¿Cada cuántas visitas se gana?", "tipo": "numero", "defecto": 10}],
    },
    "cumpleanos": {
        "nombre": "Cumpleaños",
        "ayuda": "Una vez por año, en los días cercanos al cumpleaños.",
        "campos": [
            {"clave": "dias_antes", "etiqueta": "¿Cuántos días antes del cumpleaños?", "tipo": "numero", "defecto": 3, "minimo": 0},
            {"clave": "dias_despues", "etiqueta": "¿Cuántos días después del cumpleaños?", "tipo": "numero", "defecto": 3, "minimo": 0},
        ],
    },
    "dia_semana": {
        "nombre": "Día flojo",
        "ayuda": "Para atraer gente en los días que el negocio está más tranquilo.",
        "campos": [{"clave": "dias", "etiqueta": "¿Qué días?", "tipo": "dias", "defecto": [1, 2]}],
    },
    "compra_grande": {
        "nombre": "Compra grande",
        "ayuda": "Se gana en cualquier compra que llegue a la compra mínima que elijas.",
        "campos": [],
    },
    "bienvenida": {
        "nombre": "Bienvenida",
        "ayuda": "Premia la primera visita de un cliente nuevo.",
        "campos": [],
    },
    "regreso": {
        "nombre": "Volviste",
        "ayuda": "Premia a quien vuelve después de un tiempo sin venir.",
        "campos": [{"clave": "n", "etiqueta": "¿Cuántas semanas sin venir?", "tipo": "numero", "defecto": 4}],
    },
    "fechas": {
        "nombre": "Fechas especiales",
        "ayuda": "Para una fecha puntual, como las fiestas o el Día del Padre. Hay que elegir desde y hasta.",
        "campos": [{"clave": "una_vez", "etiqueta": "Solo una vez por cliente", "tipo": "si_no", "defecto": True}],
    },
    "cliente_historico": {
        "nombre": "Cliente histórico",
        "ayuda": "Beneficio en todas sus compras para quien ya acumuló muchas visitas.",
        "campos": [{"clave": "n", "etiqueta": "¿A partir de cuántas visitas?", "tipo": "numero", "defecto": 50}],
    },
}


@dataclass
class Historial:
    hoy: date
    fechas: list = field(default_factory=list)  # una por visita no anulada; puede repetirse el día
    usos: dict = field(default_factory=dict)  # id de promo -> fechas en que se usó
    cumple_mes: int = 1
    cumple_dia: int = 1

    @property
    def puede_hoy(self):
        return self.hoy not in self.fechas

    @property
    def con_hoy(self):
        return sorted([*self.fechas, self.hoy])


def lunes(d):
    return d - timedelta(days=d.weekday())


def calcular_racha(fechas, hoy):
    """Semanas con visita. Una semana sin venir se perdona; dos seguidas cortan."""
    semanas = sorted({lunes(f) for f in fechas})
    if not semanas:
        return {"semanas": 0, "en_riesgo": False}
    atraso = (lunes(hoy) - semanas[-1]).days // 7
    if atraso > 2:
        return {"semanas": 0, "en_riesgo": False}
    total = 1
    for anterior, siguiente in zip(reversed(semanas[:-1]), reversed(semanas[1:])):
        if (siguiente - anterior).days // 7 > 2:
            break
        total += 1
    return {"semanas": total, "en_riesgo": atraso == 2}


def estado_cliente(ultima, hoy):
    """Mismo criterio que la racha: dos semanas seguidas sin venir la cortan."""
    if ultima is None:
        return {"clave": "sin_visitas", "texto": "Sin visitas"}
    atraso = (lunes(hoy) - lunes(ultima)).days // 7
    if atraso <= 1:
        return {"clave": "activo", "texto": "Activo"}
    if atraso == 2:
        return {"clave": "en_riesgo", "texto": "Por perder la racha"}
    return {"clave": "inactivo", "texto": "Dejó de venir"}


def dias_para_cumple(mes, dia, hoy):
    cumple = _cumple_del_anio(hoy.year, mes, dia)
    if cumple < hoy:
        cumple = _cumple_del_anio(hoy.year + 1, mes, dia)
    return (cumple - hoy).days


def visitas_de_la_semana(fechas, hoy):
    return sum(1 for f in fechas if lunes(f) == lunes(hoy))


def _fecha_iso(texto):
    return date.fromisoformat(texto) if texto else None


def en_vigencia(promo, dia):
    desde, hasta = _fecha_iso(promo.get("desde")), _fecha_iso(promo.get("hasta"))
    return (not desde or dia >= desde) and (not hasta or dia <= hasta)


def _cumple_del_anio(anio, mes, dia):
    try:
        return date(anio, mes, dia)
    except ValueError:  # 29 de febrero en un año común
        return date(anio, 2, 28)


def _ventanas_cumple(promo, h, anios):
    antes = timedelta(days=promo["params"].get("dias_antes", 0))
    despues = timedelta(days=promo["params"].get("dias_despues", 0))
    for anio in anios:
        cumple = _cumple_del_anio(anio, h.cumple_mes, h.cumple_dia)
        yield cumple - antes, cumple + despues


def _uso_entre(promo, h, inicio, fin):
    return any(inicio <= u <= fin for u in h.usos.get(promo["id"], []))


def _aplica(promo, h):
    tipo, params = promo["tipo"], promo["params"]
    despues = h.con_hoy
    if tipo == "visitas_semana":
        return visitas_de_la_semana(despues, h.hoy) == params["n"]
    if tipo == "racha_semanal":
        primera_de_la_semana = visitas_de_la_semana(h.fechas, h.hoy) == 0
        return primera_de_la_semana and calcular_racha(despues, h.hoy)["semanas"] % params["n"] == 0
    if tipo == "cada_n_visitas":
        return len(despues) % params["n"] == 0
    if tipo == "cumpleanos":
        for inicio, fin in _ventanas_cumple(promo, h, range(h.hoy.year - 1, h.hoy.year + 2)):
            if inicio <= h.hoy <= fin:
                return not _uso_entre(promo, h, inicio, fin)
        return False
    if tipo == "dia_semana":
        return h.hoy.weekday() in params["dias"]
    if tipo == "compra_grande":
        return True
    if tipo == "bienvenida":
        return not h.fechas
    if tipo == "regreso":
        if not h.fechas:
            return False
        semanas_sin_venir = (lunes(h.hoy) - lunes(max(h.fechas))).days // 7 - 1
        return semanas_sin_venir >= params["n"]
    if tipo == "fechas":
        return not (params.get("una_vez") and h.usos.get(promo["id"]))
    if tipo == "cliente_historico":
        return len(despues) >= params["n"]
    return False


def candidatas(promos, h):
    """Promos que la visita de hoy gana por sus condiciones, antes de mirar el monto."""
    return [p for p in promos if p["activa"] and en_vigencia(p, h.hoy) and _aplica(p, h)]


def calcular_descuento(promo, monto):
    if promo["beneficio"] == "regalo":
        return 0
    if promo["beneficio"] == "monto":
        return min(int(promo["valor"]), monto)
    descuento = (Decimal(monto) * Decimal(str(promo["valor"])) / 100).quantize(Decimal(1), ROUND_HALF_UP)
    descuento = int(descuento)
    if promo.get("techo"):
        descuento = min(descuento, promo["techo"])
    return min(descuento, monto)


def liquidar(lista, monto):
    """Los descuentos no se acumulan: gana el mayor. Los regalos se entregan aparte."""
    ganadora, descuento, regalos, no_llegan = None, 0, [], []
    for promo in lista:
        piso = promo.get("piso") or 0
        if monto is None and piso:
            continue
        if monto is not None and monto < piso:
            no_llegan.append({"nombre": promo["nombre"], "piso": piso, "faltan": piso - monto})
        elif promo["beneficio"] == "regalo":
            regalos.append(promo)
        elif monto is not None:
            propio = calcular_descuento(promo, monto)
            if ganadora is None or propio > descuento:
                ganadora, descuento = promo, propio
    return {
        "monto": monto,
        "descuento": descuento,
        "final": None if monto is None else monto - descuento,
        "promo": ganadora,
        "regalos": regalos,
        "no_llegan": no_llegan,
    }


def pesos(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


def texto_beneficio(promo):
    if promo["beneficio"] == "regalo":
        return f"de regalo: {promo.get('regalo') or 'una sorpresa'}"
    if promo["beneficio"] == "monto":
        return f"{pesos(promo['valor'])} de descuento"
    return f"{promo['valor']:g}% de descuento"


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def describir(promo):
    """Frase para el cliente, que se muestra en la pizarra de promociones."""
    tipo, params = promo["tipo"], promo["params"]
    if tipo == "visitas_semana":
        cuando = f"En tu {params['n']}.ª visita de la semana"
    elif tipo == "racha_semanal":
        cuando = f"Cada {_plural(params['n'], 'semana', 'semanas')} de racha"
    elif tipo == "cada_n_visitas":
        cuando = f"Cada {_plural(params['n'], 'visita', 'visitas')}"
    elif tipo == "cumpleanos":
        cuando = "Por tu cumpleaños"
    elif tipo == "dia_semana":
        cuando = "Los " + " y ".join(_dias_plural(params["dias"]))
    elif tipo == "compra_grande":
        cuando = "En tu compra grande"
    elif tipo == "bienvenida":
        cuando = "En tu primera visita"
    elif tipo == "regreso":
        cuando = f"Si volvés después de {_plural(params['n'], 'semana', 'semanas')}"
    elif tipo == "fechas":
        cuando = "Por tiempo limitado"
    else:
        cuando = f"Desde tu {params['n']}.ª visita"
    return f"{cuando}: {texto_beneficio(promo)}{_condiciones(promo)}"


def _dias_plural(dias):
    return [DIAS[d] + ("s" if d == 5 or d == 6 else "") for d in sorted(dias)]


def _condiciones(promo):
    partes = []
    if promo.get("piso"):
        partes.append(f"en compras desde {pesos(promo['piso'])}")
    if promo["beneficio"] == "porcentaje" and promo.get("techo"):
        partes.append(f"descuento máximo {pesos(promo['techo'])}")
    return " (" + ", ".join(partes) + ")" if partes else ""


def vigente_hoy(promo, hoy):
    """Lo que corresponde mostrar hoy en la pizarra."""
    if not promo["activa"] or not en_vigencia(promo, hoy):
        return False
    return promo["tipo"] != "dia_semana" or hoy.weekday() in promo["params"]["dias"]


def general_vigente(promo, hoy):
    """Las promociones para todos valen según sus días y sus fechas."""
    return promo["activa"] and en_vigencia(promo, hoy) and hoy.weekday() in promo["dias"]


def texto_dias(dias):
    dias = sorted(dias)
    if len(dias) == 7:
        return "Todos los días"
    if len(dias) > 2 and dias == list(range(dias[0], dias[-1] + 1)):
        return f"De {DIAS[dias[0]]} a {DIAS[dias[-1]]}"
    nombres = [DIAS[d] for d in dias]
    texto = nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]
    return texto.capitalize()


def _proximo_dia_con(condicion, desde_dia, tope=800):
    for salto in range(tope):
        dia = desde_dia + timedelta(days=salto)
        if condicion(dia):
            return dia
    return None


def _estimar(promo, h):
    """Devuelve (fecha más cercana en que podría ganarla, frase) o None."""
    tipo, params = promo["tipo"], promo["params"]
    # Para estimar el próximo premio, quien ya vino hoy recién vuelve mañana.
    inicio = h.hoy if h.puede_hoy else h.hoy + timedelta(days=1)
    domingo = lunes(h.hoy) + timedelta(days=6)
    prox_lunes = lunes(h.hoy) + timedelta(days=7)
    total = len(h.fechas)

    if tipo == "visitas_semana":
        n = params["n"]
        hechas = visitas_de_la_semana(h.fechas, h.hoy)
        falta = n - hechas
        if falta > 0 and inicio + timedelta(days=falta - 1) <= domingo:
            return inicio + timedelta(days=falta - 1), f"Te {_faltan(falta, 'visita', 'visitas')} esta semana"
        if falta == 1:
            # Varias visitas en un día cuentan: si solo falta una, puede volver hoy mismo.
            return h.hoy, "Te falta 1 visita esta semana: podés volver hoy"
        return prox_lunes + timedelta(days=n - 1), f"La semana que viene, vení {_plural(n, 'vez', 'veces')}"
    if tipo == "racha_semanal":
        n = params["n"]
        semanas = calcular_racha(h.fechas, h.hoy)["semanas"]
        falta = n - semanas % n
        base = inicio if visitas_de_la_semana(h.fechas, h.hoy) == 0 and h.puede_hoy else prox_lunes
        return base + timedelta(days=7 * (falta - 1)), f"Te {_faltan(falta, 'semana', 'semanas')} de racha"
    if tipo == "cada_n_visitas":
        falta = params["n"] - total % params["n"]
        return inicio + timedelta(days=falta - 1), f"Te {_faltan(falta, 'visita', 'visitas')}"
    if tipo == "cliente_historico":
        falta = max(params["n"] - total, 1)
        return inicio + timedelta(days=falta - 1), f"Te {_faltan(falta, 'visita', 'visitas')}"
    if tipo == "cumpleanos":
        for ini, fin in _ventanas_cumple(promo, h, range(h.hoy.year - 1, h.hoy.year + 3)):
            dia = max(ini, inicio)
            if dia <= fin and not _uso_entre(promo, h, ini, fin):
                faltan = (dia - h.hoy).days
                if faltan <= 1:
                    return dia, "Por tu cumpleaños, volvé mañana"
                return dia, f"Se acerca tu cumpleaños: en {faltan} días"
        return None
    if tipo == "dia_semana":
        dia = _proximo_dia_con(lambda d: d.weekday() in params["dias"], inicio, 7)
        return (dia, f"Vení el {DIAS[dia.weekday()]}") if dia else None
    if tipo == "compra_grande":
        return inicio, f"Comprando desde {pesos(promo.get('piso') or 0)}"
    if tipo == "fechas":
        if params.get("una_vez") and h.usos.get(promo["id"]):
            return None
        desde = _fecha_iso(promo.get("desde"))
        dia = max(inicio, desde) if desde else inicio
        return dia, f"Vení desde el {dia.day}/{dia.month}"
    return None


def _faltan(n, singular, plural):
    return f"{'falta' if n == 1 else 'faltan'} {_plural(n, singular, plural)}"


def proxima_promo(promos, h, excluir=()):
    """La promo alcanzable más cercana, para mostrarle al cliente qué le conviene."""
    excluidas = {p["id"] for p in excluir}
    opciones = []
    for promo in promos:
        if not promo["activa"] or promo["id"] in excluidas:
            continue
        estimado = _estimar(promo, h)
        if not estimado:
            continue
        dia, frase = estimado
        desde, hasta = _fecha_iso(promo.get("desde")), _fecha_iso(promo.get("hasta"))
        if desde and dia < desde:
            dia = desde
        if hasta and dia > hasta:
            continue
        opciones.append((dia, promo["id"], promo, frase))
    if not opciones:
        return None
    dia, _, promo, frase = min(opciones, key=lambda o: (o[0], o[1]))
    return {
        "nombre": promo["nombre"],
        "tipo": promo["tipo"],
        "frase": frase,
        "beneficio": texto_beneficio(promo) + _condiciones(promo),
        "dias": (dia - h.hoy).days,
    }
