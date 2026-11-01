"use strict";

const app = document.getElementById("app");
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const MINUTOS_SIN_USO = 2;

const TRAZOS = {
  visitas_semana: "M12 3c1 4 5 5.5 5 10.5a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 .3 1.5 1 2.5 2 3 .5-3-.5-6 1-9z",
  racha_semanal: "M4 6h16v14H4z M4 10h16 M8 3v4 M16 3v4 M9 15l2 2 4-4",
  cada_n_visitas: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.5 2.9 1-6.1L3.1 9.5l6.1-.9z",
  cumpleanos: "M4 20h16v-7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2z M4 15c2 2 3 2 4 0 1 2 3 2 4 0 1 2 3 2 4 0 1 2 2 2 4 0 M12 11V7 M12 3v1",
  dia_semana: "M4 6h16v14H4z M4 10h16 M8 3v4 M16 3v4 M11 13h2v2h-2z",
  compra_grande: "M6 9c2-5 10-6 13-2 3 5-1 11-6 11-2 0-3-2-5-2s-3-1-3-3 0-3 1-4z M12 9.5a1.5 1.5 0 1 0 .01 0",
  bienvenida: "M12 20s-8-5-8-11a4.5 4.5 0 0 1 8-2.5A4.5 4.5 0 0 1 20 9c0 6-8 11-8 11z",
  regreso: "M9 5L4 10l5 5 M4 10h10a5 5 0 0 1 0 10h-3",
  fechas: "M4 11h16v9H4z M3 7h18v4H3z M12 7v13 M12 7c-3 0-5-4-2-4s2 4 2 4z M12 7c3 0 5-4 2-4s-2 4-2 4z",
  cliente_historico: "M7 4h10v6a5 5 0 0 1-10 0z M7 6H4c0 3 1 5 3 5 M17 6h3c0 3-1 5-3 5 M12 15v4 M8 20h8",
  general: "M6 18L18 6 M8 5.5a2 2 0 1 0 .01 0 M16 14.5a2 2 0 1 0 .01 0",
};

let estado = { vista: "inicio" };
let temporizador = null;

const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const conPuntos = (t) => (t ? Number(t).toLocaleString("es-AR", { maximumFractionDigits: 0 }) : "");
const pesos = (n) => "$ " + Number(n).toLocaleString("es-AR", { maximumFractionDigits: 0 });
const primerNombre = (nombre) => nombre.split(" ")[0];
const digitos = (t) => String(t).replace(/\D/g, "");
const icono = (tipo) => `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path d="${TRAZOS[tipo] ?? TRAZOS.general}"/></svg>`;
const circulo = (tipo) => `<span class="circulo">${icono(tipo)}</span>`;
const ICONOS_GENERALES = {
  vaca: { texto: "Vaca de Joaquín", html: `<span class="circulo"><img src="/vaca.png" alt=""></span>` },
  cuenta_dni: { texto: "Cuenta DNI", html: `<span class="circulo claro"><img src="/cuenta-dni.png" alt=""></span>` },
  general: { texto: "Porcentaje", html: circulo("general") },
};
const circuloGeneral = (g) => (ICONOS_GENERALES[g.icono] ?? ICONOS_GENERALES.general).html;

async function api(ruta, metodo = "GET", datos) {
  const opciones = { method: metodo };
  if (metodo === "POST" || metodo === "PUT") {
    opciones.headers = { "Content-Type": "application/json" };
    opciones.body = JSON.stringify(datos ?? {});
  }
  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw Object.assign(new Error("El programa no responde. Cerralo y volvé a abrirlo."), { estado: 0 });
  }
  const cuerpo = await respuesta.json();
  if (!respuesta.ok) throw Object.assign(new Error(cuerpo.error), { estado: respuesta.status });
  return cuerpo;
}

function avisar(texto, error = false) {
  const aviso = document.getElementById("aviso");
  aviso.textContent = texto;
  aviso.className = error ? "aviso error" : "aviso";
  aviso.hidden = false;
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => { aviso.hidden = true; }, error ? 6000 : 3000);
}

function mostrar(vista, html, datos = {}) {
  estado = { vista, ...datos };
  app.innerHTML = html;
  window.scrollTo(0, 0);
  const pestania = ["promos", "movimientos", "formulario-movimiento", "clientes", "perfil", "editar-cliente"].includes(vista) ? "promos" : "inicio";
  document.querySelectorAll(".pestania").forEach((b) => {
    const activa = b.dataset.pestania === pestania;
    b.classList.toggle("activa", activa);
    if (activa) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  // Con Enter se avanza pantalla por pantalla, sin tocar el mouse.
  app.querySelector("[data-foco]")?.focus();
  reiniciarTemporizador();
}

// Vuelve solo al inicio para que el próximo cliente no vea la ficha del anterior.
function reiniciarTemporizador() {
  clearTimeout(temporizador);
  const seVuelve = ["ficha", "perfil", "clientes", "movimientos"].includes(estado.vista);
  if (seVuelve || (estado.vista === "resultado" && !estado.conDescuento)) {
    temporizador = setTimeout(irInicio, MINUTOS_SIN_USO * 60000);
  }
}

const mostrarError = (texto) => { document.getElementById("error").textContent = texto; };

// Inicio

async function irInicio() {
  const datos = await api("/api/inicio").catch((e) => { avisar(e.message, true); return { promos: [], generales: [] }; });
  const todos = datos.generales.length
    ? `<div class="grilla-todos">${datos.generales.map((g) => `
        <article class="promo-todos">
          ${circuloGeneral(g)}
          <div>
            <h3>${esc(g.nombre)}</h3>
            <p>${esc(g.descripcion)}</p>
            <p class="dias">${esc(g.texto_dias)}</p>
          </div>
        </article>`).join("")}</div>`
    : `<p class="sin-promos">Hoy no hay promociones para todos.</p>`;
  // Las promos del mismo tipo, como las dos de la racha semanal, van en un solo renglón.
  const grupos = new Map();
  datos.promos.forEach((p) => grupos.set(p.tipo, [...(grupos.get(p.tipo) ?? []), p]));
  const club = [...grupos.values()].map((g) => `
    <li>${circulo(g[0].tipo)}<span><strong>${esc(g.length > 1 ? g[0].mecanismo : g[0].nombre)}</strong>
      ${g.map((p) => `<span class="detalle">${esc(p.descripcion)}</span>`).join("")}</span></li>`).join("");
  mostrar("inicio", `
    <div class="inicio">
      <div class="columna">
        <form class="tarjeta dni" data-form="dni" novalidate>
          <h1><label for="entrada">Ingresá tu DNI</label></h1>
          <p class="dni-sub">Mirá tu racha y tus premios</p>
          <div class="dni-fila">
            <div class="campo-grande">
              <input id="entrada" data-foco data-numero data-maximo="8" inputmode="numeric" autocomplete="off" placeholder="Escribí el número">
            </div>
            <button class="boton principal">Buscar</button>
          </div>
          <div class="dni-pie">
            <p id="error" class="mensaje-error" role="alert"></p>
            <button type="button" class="enlace" data-accion="ir-alta">Anotar un cliente nuevo</button>
          </div>
        </form>
        <section class="para-todos">
          <h2>Promociones de hoy <span>para todos</span></h2>
          ${todos}
        </section>
      </div>
      <section class="club">
        <h2>Beneficios del club</h2>
        <p class="club-sub">Mientras más venís, más ganás</p>
        <ul>${club}</ul>
        <p class="invitacion">¿Todavía no sos del club? ¡Pedí que te anoten!</p>
      </section>
    </div>`);
}

async function buscarDni(form) {
  const dni = digitos(form.elements.entrada.value);
  if (dni.length < 7) {
    mostrarError("El DNI tiene 7 u 8 números.");
    return;
  }
  try {
    irFicha(await api(`/api/clientes/${dni}`));
  } catch (e) {
    if (e.estado === 404) irNoEncontrado(dni);
    else mostrarError(e.message);
  }
}

function irNoEncontrado(dni) {
  mostrar("no-encontrado", `
    <section class="central tarjeta">
      <h1>Todavía no está anotado</h1>
      <p class="bajada">No hay ningún cliente con el DNI&nbsp;<b>${esc(conPuntos(dni))}</b></p>
      <div class="acciones">
        <button class="boton principal" data-foco data-accion="ir-alta" data-dni="${esc(dni)}">Anotarlo ahora</button>
        <button class="boton" data-accion="ir-inicio">Volver y corregir</button>
      </div>
    </section>`);
}

// Alta y edición de clientes

function irFormularioCliente(cliente, dni = "") {
  const c = cliente ?? { dni, nombre: "", telefono: "", cumple_dia: "", cumple_mes: "" };
  const opcionesDia = Array.from({ length: 31 }, (_, i) => i + 1)
    .map((d) => `<option value="${d}" ${d === c.cumple_dia ? "selected" : ""}>${d}</option>`).join("");
  const opcionesMes = MESES
    .map((m, i) => `<option value="${i + 1}" ${i + 1 === c.cumple_mes ? "selected" : ""}>${m}</option>`).join("");
  mostrar(cliente ? "editar-cliente" : "formulario-cliente", `
    <form class="formulario tarjeta" id="form-cliente" data-id="${cliente ? cliente.id : ""}">
      <h1>${cliente ? "Cambiar datos del cliente" : "Anotar un cliente nuevo"}</h1>
      <label class="campo"><span>Nombre y apellido</span>
        <input name="nombre" data-foco value="${esc(c.nombre)}" autocomplete="off" required></label>
      <label class="campo"><span>DNI</span>
        <small>Solo números, sin puntos.</small>
        <input name="dni" value="${esc(c.dni)}" inputmode="numeric" autocomplete="off" required></label>
      <div class="dos-campos">
        <label class="campo"><span>Día del cumpleaños</span>
          <select name="cumple_dia" required><option value="">Elegir</option>${opcionesDia}</select></label>
        <label class="campo"><span>Mes del cumpleaños</span>
          <select name="cumple_mes" required><option value="">Elegir</option>${opcionesMes}</select></label>
      </div>
      <label class="campo"><span>Teléfono (si quiere dejarlo)</span>
        <small>No le vamos a mandar mensajes.</small>
        <input name="telefono" value="${esc(c.telefono)}" inputmode="tel" autocomplete="off"></label>
      ${cliente ? "" : `
      <label class="opcion acepta"><input type="checkbox" name="consentimiento">
        <span>El cliente aceptó que guardemos sus datos para usarlos solo en este club de beneficios.</span></label>`}
      <p id="error" class="mensaje-error" role="alert"></p>
      <div class="acciones">
        <button class="boton principal" type="submit">Guardar</button>
        ${cliente
          ? `<button class="boton" type="button" data-accion="ver-perfil" data-dni="${esc(cliente.dni)}">Cancelar</button>`
          : `<button class="boton" type="button" data-accion="ir-inicio">Cancelar</button>`}
      </div>
    </form>`);
}

async function guardarCliente(form) {
  const f = new FormData(form);
  const datos = Object.fromEntries(f.entries());
  datos.consentimiento = f.has("consentimiento");
  try {
    const ficha = form.dataset.id
      ? await api(`/api/clientes/${form.dataset.id}`, "PUT", datos)
      : await api("/api/clientes", "POST", datos);
    avisar("¡Datos guardados!");
    if (form.dataset.id) irPerfil(ficha.cliente.dni);
    else irFicha(ficha);
  } catch (e) {
    mostrarError(e.message);
  }
}

// Ficha

const bloqueProxima = (p) => (p ? `
  <section class="proxima">
    ${circulo(p.tipo)}
    <div>
      <h2>Tu próximo premio</h2>
      <p class="frase">${esc(p.frase)}</p>
      <p class="gana">y ganás ${esc(p.beneficio)}</p>
    </div>
  </section>` : "");

function fueguitos(hechas, meta) {
  return `<div class="fueguitos" aria-hidden="true">${Array.from({ length: meta }, (_, i) =>
    `<span class="${i < hechas ? "" : "apagado"}">${icono("visitas_semana")}</span>`).join("")}</div>`;
}

function irFicha(ficha) {
  const { cliente, racha } = ficha;
  const meta = ficha.meta_semana;
  const semana = meta && meta <= 7
    ? `${fueguitos(ficha.visitas_semana, meta)}<div class="pie">${ficha.visitas_semana} de ${meta} visitas esta semana</div>`
    : `<div class="cifra">${ficha.visitas_semana}</div><div class="pie">visitas esta semana</div>`;
  const pieRacha = racha.en_riesgo
    ? `<div class="pie alerta">¡Vení esta semana o se corta!</div>`
    : `<div class="pie">${racha.semanas === 1 ? "semana" : "semanas"} de racha</div>`;
  const premio = ficha.hoy_tiene.length ? `
    <section class="premio-hoy">
      <h2>¡Hoy tenés premio!</h2>
      ${ficha.hoy_tiene.map((p) => `<p>${circulo(p.tipo)}${esc(p.descripcion)}</p>`).join("")}
    </section>` : "";
  // Enter queda en Terminar para que no se sume otra visita sin querer.
  const accion = ficha.visitas_hoy
    ? `<div class="ya-vino">✓ Hoy ya sumó ${ficha.visitas_hoy === 1 ? "1 visita" : `${ficha.visitas_hoy} visitas`}. ¡Gracias por venir!</div>
       <button class="boton principal gigante" data-accion="sumar-visita">Volvió: sumar otra visita</button>
       <div class="acciones">
         <button class="boton" data-foco data-accion="ir-inicio">Terminar</button>
         <button class="boton discreto" data-accion="anular" data-visita="${ficha.ultima_visita_hoy_id}">Me equivoqué: anular la última</button>
       </div>`
    : `<button class="boton principal gigante" data-foco data-accion="sumar-visita">Sumar la visita de hoy</button>
       <div class="acciones">
         <button class="boton" data-accion="ir-inicio">Volver sin sumar</button>
       </div>`;
  mostrar("ficha", `
    <div class="saludo">
      <h1>¡Hola, ${esc(primerNombre(cliente.nombre))}!</h1>
    </div>
    <div class="medidores">
      <div class="medidor"><h3>Racha semanal</h3>${semana}</div>
      <div class="medidor"><h3>Racha acumulada</h3><div class="cifra">${racha.semanas}</div>${pieRacha}</div>
      <div class="medidor"><h3>Visitas en total</h3><div class="cifra">${ficha.total_visitas}</div><div class="pie">¡gracias por elegirnos!</div></div>
    </div>
    ${premio}
    ${ficha.hoy_tiene.length ? "" : bloqueProxima(ficha.proxima)}
    ${accion}`, { ficha });
}

// Registrar una visita

async function sumarVisita() {
  const ficha = estado.ficha;
  try {
    const previa = await api("/api/visitas/vista-previa", "POST", { cliente_id: ficha.cliente.id });
    irMonto(ficha, previa.candidatas);
  } catch (e) {
    avisar(e.message, true);
  }
}

function irMonto(ficha, candidatas) {
  mostrar("monto", `
    <form class="central tarjeta" data-form="monto" novalidate>
      <h1>${candidatas.length ? "¡Tiene un beneficio!" : "Sumemos la visita"}</h1>
      ${candidatas.map((p) => `<p class="bajada">${circulo(p.tipo)}${esc(p.descripcion)}</p>`).join("")}
      <h2 class="pregunta"><label for="entrada">¿Cuánto salió la compra?</label></h2>
      <p class="dni-sub">Poné el total que marcó la caja${candidatas.length ? ", antes del descuento" : ""}</p>
      <div class="campo-grande">
        <b aria-hidden="true">$</b>
        <input id="entrada" data-foco data-numero data-maximo="9" inputmode="numeric" autocomplete="off" placeholder="Escribí el monto">
      </div>
      <p id="error" class="mensaje-error" role="alert"></p>
      <button class="boton principal gigante">${candidatas.length ? "Calcular el descuento" : "Sumar la visita"}</button>
      <div class="acciones">
        <button type="button" class="boton" data-accion="volver-ficha">Volver</button>
      </div>
    </form>`, { ficha, candidatas });
}

const bloqueTicket = (liq) => `
  <div class="ticket">
    <div class="fila"><span>Compra</span><span>${pesos(liq.monto)}</span></div>
    ${liq.promo ? `<div class="fila descuento"><span>Descuento: ${esc(liq.promo.nombre)}</span><span>− ${pesos(liq.descuento)}</span></div>` : ""}
    <div class="fila total"><span>A cobrar</span><b>${pesos(liq.final)}</b></div>
  </div>`;

const bloqueRegalos = (liq) => liq.regalos.map((r) => `<div class="regalo">Se lleva de regalo: ${esc(r.regalo)}</div>`).join("");
const bloqueNoLlega = (liq) => liq.no_llegan.map((n) =>
  `<div class="no-llega">${esc(n.nombre)}: pide compras desde ${pesos(n.piso)}. Le faltan ${pesos(n.faltan)}.</div>`).join("");

async function calcular(form) {
  const monto = Number(digitos(form.elements.entrada.value));
  if (!monto) {
    mostrarError("Poné el monto de la compra.");
    return;
  }
  if (!estado.candidatas.length) return confirmarVisita(estado.ficha, monto);
  try {
    const previa = await api("/api/visitas/vista-previa", "POST", { cliente_id: estado.ficha.cliente.id, monto });
    irCuenta(previa.liquidacion, monto);
  } catch (e) {
    mostrarError(e.message);
  }
}

function irCuenta(liq, monto) {
  const { ficha, candidatas } = estado;
  mostrar("cuenta", `
    <section class="central tarjeta">
      <h1>${liq.promo ? "¡Descuento aplicado!" : "Sin descuento en esta compra"}</h1>
      ${liq.promo ? `<p class="bajada">${circulo(liq.promo.tipo)}${esc(liq.promo.descripcion)}</p>` : ""}
      ${bloqueNoLlega(liq)}
      ${bloqueTicket(liq)}
      ${bloqueRegalos(liq)}
      <button class="boton principal gigante" data-foco data-accion="confirmar">Listo, sumar la visita</button>
      <div class="acciones">
        <button class="boton" data-accion="corregir-monto">Corregir el monto</button>
      </div>
    </section>`, { ficha, candidatas, monto });
}

async function confirmarVisita(ficha, monto) {
  try {
    const r = await api("/api/visitas", "POST", { cliente_id: ficha.cliente.id, monto });
    irResultado(ficha, r);
  } catch (e) {
    avisar(e.message, true);
  }
}

function irResultado(ficha, r) {
  const liq = r.liquidacion;
  const nombre = esc(primerNombre(ficha.cliente.nombre));
  const huboPremio = Boolean(liq.promo || liq.regalos.length);
  const botones = `
    <div class="acciones">
      <button class="boton principal" data-foco data-accion="ir-inicio">Terminar</button>
      <button class="boton discreto" data-accion="anular" data-visita="${r.visita_id}">Me equivoqué: anular</button>
    </div>`;
  if (huboPremio) {
    mostrar("resultado", `
      <section class="central tarjeta">
        <h1>¡Felicitaciones, ${nombre}!</h1>
        ${liq.promo ? `<p class="bajada">${circulo(liq.promo.tipo)}Ganaste: ${esc(liq.promo.nombre)}</p>` : ""}
        ${bloqueTicket(liq)}
        ${bloqueRegalos(liq)}
        ${bloqueProxima(r.proxima)}
        ${botones}
      </section>`, { conDescuento: Boolean(liq.promo) });
    festejar();
    return;
  }
  const p = r.proxima;
  mostrar("resultado", `
    <section class="central">
      <div class="afiche">
        <h1>¡Visita sumada, ${nombre}!</h1>
        ${p ? `
          ${circulo(p.tipo)}
          <p class="etiqueta">Tu próximo premio</p>
          <p class="frase">${esc(p.frase)}</p>
          <p class="gana">y ganás ${esc(p.beneficio)}</p>`
        : `<p class="frase">¡Gracias por venir!</p>`}
        <p class="etiqueta">Racha acumulada: ${r.racha.semanas} ${r.racha.semanas === 1 ? "semana" : "semanas"}</p>
      </div>
      ${botones}
    </section>`, { conDescuento: false });
}

function festejar() {
  const colores = ["#d2232a", "#8fd0ee", "#121212", "#ffffff"];
  for (let i = 0; i < 60; i++) {
    const pieza = document.createElement("span");
    pieza.className = "papel-picado";
    pieza.style.left = Math.random() * 100 + "vw";
    pieza.style.background = colores[i % colores.length];
    pieza.style.animationDelay = Math.random() * 0.9 + "s";
    pieza.addEventListener("animationend", () => pieza.remove());
    document.body.append(pieza);
  }
}

async function anular(visitaId) {
  if (!confirm("¿Seguro que querés anular esta visita?")) return;
  try {
    await api(`/api/visitas/${visitaId}/anular`, "POST");
    avisar("Visita anulada.");
    if (["movimientos", "perfil"].includes(estado.vista)) alVolver();
    else irInicio();
  } catch (e) {
    avisar(e.message, true);
  }
}

// Pestaña Movimientos

const FILTROS_VACIOS = { texto: "", desde: "", hasta: "", limite: 50 };
let filtros = { ...FILTROS_VACIOS };
// Adónde volver después de tocar un movimiento: la lista o el perfil del cliente.
let alVolver = () => irMovimientos();

async function irMovimientos() {
  alVolver = () => irMovimientos();
  try {
    const consulta = new URLSearchParams(filtros);
    const { movimientos, total, hoy } = await api(`/api/movimientos?${consulta}`);
    const hayFiltros = filtros.texto || filtros.desde || filtros.hasta;
    mostrar("movimientos", `
      <div class="promos-cabecera">
        <div>
          <h1>Movimientos</h1>
          <p>Todas las visitas registradas. Si hubo un error se puede cambiar o anular, y si faltó alguna se puede cargar acá.</p>
        </div>
        <div class="filtros-botones">
          <button class="boton" data-accion="ir-promos">Volver a Promociones</button>
          <button class="boton principal" data-accion="nuevo-movimiento">+ Cargar una visita olvidada</button>
        </div>
      </div>
      <form class="tarjeta filtros" data-form="filtro-movimientos">
        <label class="campo"><span>Buscar por nombre o DNI</span>
          <input name="texto" value="${esc(filtros.texto)}" autocomplete="off"></label>
        <label class="campo"><span>Desde</span><input type="date" name="desde" value="${esc(filtros.desde)}" max="${hoy}"></label>
        <label class="campo"><span>Hasta</span><input type="date" name="hasta" value="${esc(filtros.hasta)}" max="${hoy}"></label>
        <div class="filtros-botones">
          <button class="boton">Buscar</button>
          ${hayFiltros ? `<button type="button" class="boton discreto" data-accion="ir-movimientos">Ver todos</button>` : ""}
        </div>
      </form>
      ${movimientos.length ? `
      <div class="tabla-contenedor tarjeta">
        <table class="tabla">
          <thead><tr><th>Fecha</th><th>Cliente</th><th class="num">Compra</th><th class="num">Descuento</th><th class="num">Cobrado</th><th>Beneficio</th><th><span class="oculto">Acciones</span></th></tr></thead>
          <tbody>${movimientos.map(filaMovimiento).join("")}</tbody>
        </table>
      </div>
      <div class="pie-tabla">
        <span>Mostrando ${movimientos.length} de ${total}</span>
        ${total > movimientos.length ? `<button class="boton" data-accion="mas-movimientos">Ver más</button>` : ""}
      </div>` : `<p class="tarjeta sin-movimientos">${hayFiltros ? "No hay movimientos con esa búsqueda." : "Todavía no hay movimientos."}</p>`}`,
      { movimientos, hoy });
  } catch (e) {
    avisar(e.message, true);
  }
}

function filaMovimiento(m) {
  const notas = [
    ...m.beneficios.map((b) => esc(b.nombre)),
    m.anulada ? "<b>Anulada</b>" : "",
    m.modificada ? `<small>Modificada el ${fechaCorta(m.modificada)}</small>` : "",
  ].filter(Boolean).join("<br>");
  const acciones = m.anulada
    ? `<button class="boton chica" data-accion="recuperar" data-visita="${m.id}">Recuperar</button>`
    : `<button class="boton chica" data-accion="editar-movimiento" data-visita="${m.id}">Cambiar</button>
       <button class="boton chica discreto" data-accion="anular" data-visita="${m.id}">Anular</button>`;
  const importe = (n) => (n === null ? "—" : pesos(n));
  return `
    <tr class="${m.anulada ? "anulada" : ""}">
      <td>${fechaCorta(m.fecha)}</td>
      <td><b>${esc(m.nombre)}</b><br><small>DNI ${esc(conPuntos(m.dni))}</small></td>
      <td class="num">${importe(m.monto)}</td>
      <td class="num">${m.descuento ? "− " + pesos(m.descuento) : "—"}</td>
      <td class="num"><b>${importe(m.final)}</b></td>
      <td>${notas || "—"}</td>
      <td class="acciones-fila">${acciones}</td>
    </tr>`;
}

function filtrarMovimientos(form) {
  const f = new FormData(form);
  filtros = { texto: f.get("texto").trim(), desde: f.get("desde"), hasta: f.get("hasta"), limite: FILTROS_VACIOS.limite };
  return irMovimientos();
}

async function recuperar(visitaId) {
  try {
    await api(`/api/visitas/${visitaId}/recuperar`, "POST");
    avisar("Visita recuperada.");
    alVolver();
  } catch (e) {
    avisar(e.message, true);
  }
}

async function irFormularioMovimiento(m, dni = "") {
  const { hoy } = estado;
  try {
    const { promos } = await api("/api/promos");
    const usados = new Set((m?.beneficios ?? []).map((b) => b.id));
    const opciones = promos.filter((p) => p.activa || usados.has(p.id));
    mostrar("formulario-movimiento", `
      <form class="formulario tarjeta" data-form="movimiento" data-id="${m ? m.id : ""}">
        <h1>${m ? "Cambiar movimiento" : "Cargar una visita olvidada"}</h1>
        <p class="ayuda-form">Acá no se calculan premios: poné lo que realmente pasó y lo que se cobró. Las rachas se actualizan solas.</p>
        <div class="dos-campos">
          <label class="campo"><span>DNI del cliente</span>
            <input name="dni" data-foco value="${esc(m?.dni ?? dni)}" inputmode="numeric" autocomplete="off" required></label>
          <label class="campo"><span>Fecha de la visita</span>
            <input type="date" name="fecha" value="${esc(m?.fecha ?? hoy)}" max="${hoy}" required></label>
          <label class="campo"><span>Compra en pesos</span>
            <small>Si no lo sabés, dejalo vacío.</small>
            <input type="number" min="1" step="1" name="monto" value="${m?.monto ?? ""}"></label>
          <label class="campo"><span>Descuento en pesos</span>
            <small>Si no hubo, dejalo vacío.</small>
            <input type="number" min="0" step="1" name="descuento" value="${m?.descuento || ""}"></label>
        </div>
        <p class="cobrado">Cobrado: <b id="cobrado"></b></p>
        <fieldset class="grupo"><legend>¿Usó algún beneficio?</legend>
          <small>Marcalo para que no lo pueda volver a usar, como el de cumpleaños.</small>
          <div class="opciones">
            ${opciones.map((p) => `<label class="opcion"><input type="checkbox" name="promo_ids" value="${p.id}" ${usados.has(p.id) ? "checked" : ""}>${esc(p.nombre)}</label>`).join("")}
          </div>
        </fieldset>
        <p class="mensaje-error" data-error role="alert"></p>
        <div class="acciones">
          <button class="boton principal">Guardar</button>
          <button type="button" class="boton" data-accion="volver-movimientos">Cancelar</button>
        </div>
      </form>`, { hoy });
    actualizarCobrado(app.querySelector("form"));
  } catch (e) {
    avisar(e.message, true);
  }
}

function actualizarCobrado(form) {
  const monto = Number(form.elements.monto.value);
  const descuento = Number(form.elements.descuento.value);
  document.getElementById("cobrado").textContent = monto ? pesos(Math.max(monto - descuento, 0)) : "—";
}

async function guardarMovimiento(form) {
  const f = new FormData(form);
  const entero = (clave) => (f.get(clave) === "" ? null : Number(f.get(clave)));
  const datos = {
    dni: f.get("dni"),
    fecha: f.get("fecha"),
    monto: entero("monto"),
    descuento: entero("descuento"),
    promo_ids: f.getAll("promo_ids").map(Number),
  };
  try {
    if (form.dataset.id) await api(`/api/movimientos/${form.dataset.id}`, "PUT", datos);
    else await api("/api/movimientos", "POST", datos);
    avisar("Movimiento guardado.");
    alVolver();
  } catch (e) {
    form.querySelector("[data-error]").textContent = e.message;
  }
}

// Clientes y perfil

const FILTROS_CLIENTES_VACIOS = { texto: "", estado: "", limite: 50 };
let filtrosClientes = { ...FILTROS_CLIENTES_VACIOS };
const ESTADOS = { activo: "Activo", en_riesgo: "Por perder la racha", inactivo: "Dejó de venir", sin_visitas: "Sin visitas" };
const pildora = (e) => `<span class="pildora ${esc(e.clave)}">${esc(e.texto)}</span>`;

async function irClientes() {
  try {
    const { clientes, total } = await api(`/api/clientes?${new URLSearchParams(filtrosClientes)}`);
    const hayFiltros = filtrosClientes.texto || filtrosClientes.estado;
    mostrar("clientes", `
      <div class="promos-cabecera">
        <div>
          <h1>Clientes</h1>
          <p>Todos los clientes anotados, empezando por los que vinieron hace menos. Entrá a un perfil para ver toda su información.</p>
        </div>
        <button class="boton" data-accion="ir-promos">Volver a Promociones</button>
      </div>
      <form class="tarjeta filtros filtros-clientes" data-form="filtro-clientes">
        <label class="campo"><span>Buscar por nombre o DNI</span>
          <input name="texto" value="${esc(filtrosClientes.texto)}" autocomplete="off"></label>
        <label class="campo"><span>Estado</span>
          <select name="estado"><option value="">Todos</option>
            ${Object.entries(ESTADOS).map(([clave, texto]) => `<option value="${clave}" ${filtrosClientes.estado === clave ? "selected" : ""}>${texto}</option>`).join("")}
          </select></label>
        <div class="filtros-botones">
          <button class="boton">Buscar</button>
          ${hayFiltros ? `<button type="button" class="boton discreto" data-accion="ir-clientes">Ver todos</button>` : ""}
        </div>
      </form>
      ${clientes.length ? `
      <div class="tabla-contenedor tarjeta">
        <table class="tabla">
          <thead><tr><th>Cliente</th><th>Estado</th><th>Última visita</th><th class="num">Visitas</th><th class="num">Total comprado</th><th><span class="oculto">Acciones</span></th></tr></thead>
          <tbody>${clientes.map((c) => `
            <tr>
              <td><b>${esc(c.nombre)}</b><br><small>DNI ${esc(conPuntos(c.dni))}</small></td>
              <td>${pildora(c.estado)}</td>
              <td>${c.ultima ? fechaCorta(c.ultima) : "—"}</td>
              <td class="num">${c.visitas}</td>
              <td class="num">${c.comprado ? pesos(c.comprado) : "—"}</td>
              <td class="acciones-fila"><button class="boton chica" data-accion="ver-perfil" data-dni="${esc(c.dni)}">Ver perfil</button></td>
            </tr>`).join("")}</tbody>
        </table>
      </div>
      <div class="pie-tabla">
        <span>Mostrando ${clientes.length} de ${total}</span>
        ${total > clientes.length ? `<button class="boton" data-accion="mas-clientes">Ver más</button>` : ""}
      </div>` : `<p class="tarjeta sin-movimientos">${hayFiltros ? "No hay clientes con esa búsqueda." : "Todavía no hay clientes anotados."}</p>`}`);
  } catch (e) {
    avisar(e.message, true);
  }
}

function filtrarClientes(form) {
  const f = new FormData(form);
  filtrosClientes = { texto: f.get("texto").trim(), estado: f.get("estado"), limite: FILTROS_CLIENTES_VACIOS.limite };
  return irClientes();
}

function textoUltimaVisita(p) {
  if (!p.ultima_visita) return "Todavía no vino";
  if (p.dias_sin_venir === 0) return "Hoy";
  if (p.dias_sin_venir === 1) return "Ayer";
  return `Hace ${p.dias_sin_venir} días (${fechaCorta(p.ultima_visita)})`;
}

function textoCumple(p) {
  const { cumple_dia: dia, cumple_mes: mes } = p.cliente;
  const falta = p.dias_para_cumple === 0 ? "¡es hoy!" : p.dias_para_cumple === 1 ? "es mañana" : `faltan ${p.dias_para_cumple} días`;
  return `${dia} de ${MESES[mes - 1]} (${falta})`;
}

async function irPerfil(dni) {
  alVolver = () => irPerfil(dni);
  try {
    const p = await api(`/api/clientes/${dni}/perfil`);
    const { cliente, racha } = p;
    const dato = (titulo, valor) => `<div><dt>${titulo}</dt><dd>${valor}</dd></div>`;
    const cifra = (titulo, valor) => `<div class="medidor"><h3>${titulo}</h3><div class="cifra chica">${valor}</div></div>`;
    const sinMonto = p.total_visitas - p.con_monto;
    mostrar("perfil", `
      <div class="promos-cabecera">
        <div>
          <h1>${esc(cliente.nombre)}</h1>
          <p>${pildora(p.estado)}</p>
        </div>
        <div class="filtros-botones">
          <button class="boton" data-accion="ir-clientes-volver">Volver a Clientes</button>
          <button class="boton" data-accion="editar-cliente">Cambiar datos</button>
        </div>
      </div>
      <div class="medidores cuatro">
        ${cifra("Visitas", p.total_visitas)}
        ${cifra("Total comprado", pesos(p.comprado))}
        ${cifra("Total ahorrado", pesos(p.ahorrado))}
        ${cifra("Compra promedio", p.promedio ? pesos(p.promedio) : "—")}
      </div>
      ${sinMonto > 0 ? `<p class="nota-perfil">${sinMonto === 1 ? "1 visita no tiene" : `${sinMonto} visitas no tienen`} monto cargado y no ${sinMonto === 1 ? "suma" : "suman"} en estos totales.</p>` : ""}
      <div class="perfil-grilla">
        <section class="tarjeta">
          <h2>Datos</h2>
          <dl class="datos">
            ${dato("DNI", esc(conPuntos(cliente.dni)))}
            ${dato("Cumpleaños", esc(textoCumple(p)))}
            ${dato("Teléfono", esc(cliente.telefono) || "—")}
            ${dato("Anotado el", fechaCorta(cliente.consentimiento))}
          </dl>
        </section>
        <section class="tarjeta">
          <h2>Estado</h2>
          <dl class="datos">
            ${dato("Última visita", esc(textoUltimaVisita(p)))}
            ${dato("Primera visita", p.primera_visita ? fechaCorta(p.primera_visita) : "—")}
            ${dato("Racha acumulada", `${racha.semanas} ${racha.semanas === 1 ? "semana" : "semanas"}${racha.en_riesgo ? " (se corta si no viene esta semana)" : ""}`)}
            ${dato("Visitas esta semana", p.visitas_semana)}
          </dl>
        </section>
        <section class="tarjeta">
          <h2>Beneficios</h2>
          <dl class="datos">
            ${dato("En su próxima visita", p.hoy_tiene.length ? p.hoy_tiene.map((b) => esc(b.descripcion)).join("<br>") : "Sin premio")}
            ${dato("Próximo premio", p.proxima ? `${esc(p.proxima.frase)}: ${esc(p.proxima.beneficio)}` : "—")}
          </dl>
        </section>
        <section class="tarjeta">
          <h2>Beneficios usados</h2>
          ${p.beneficios_usados.length ? `<dl class="datos">
            ${p.beneficios_usados.map((u) => dato(esc(u.nombre), `${u.veces} ${u.veces === 1 ? "vez" : "veces"}, la última el ${fechaCorta(u.ultima)}`)).join("")}
          </dl>` : `<p class="sin-datos">Todavía no usó ninguno.</p>`}
        </section>
      </div>
      <div class="promos-cabecera perfil-movimientos">
        <h2>Últimos movimientos</h2>
        <div class="filtros-botones">
          ${p.total > p.movimientos.length ? `<button class="boton" data-accion="movimientos-de" data-dni="${esc(cliente.dni)}">Ver todos (${p.total})</button>` : ""}
          <button class="boton" data-accion="nuevo-movimiento-de" data-dni="${esc(cliente.dni)}">+ Cargar una visita olvidada</button>
        </div>
      </div>
      ${p.movimientos.length ? `
      <div class="tabla-contenedor tarjeta">
        <table class="tabla">
          <thead><tr><th>Fecha</th><th>Cliente</th><th class="num">Compra</th><th class="num">Descuento</th><th class="num">Cobrado</th><th>Beneficio</th><th><span class="oculto">Acciones</span></th></tr></thead>
          <tbody>${p.movimientos.map(filaMovimiento).join("")}</tbody>
        </table>
      </div>` : `<p class="tarjeta sin-movimientos">Todavía no tiene movimientos.</p>`}`,
      { perfil: p, movimientos: p.movimientos, hoy: p.hoy });
  } catch (e) {
    avisar(e.message, true);
  }
}

// Pestaña Promociones

async function irPromos(abierta = null) {
  try {
    const { promos, mecanismos, generales } = await api("/api/promos");
    mostrar("promos", `
      <section class="seccion-promos">
        <div class="promos-cabecera">
          <div>
            <h1>Promociones para todos</h1>
            <p>Las ofertas del negocio, como Ganga Meat o Cuenta DNI. Se muestran en el inicio los días que correspondan. Son solo informativas: se cobran en la caja como siempre.</p>
          </div>
          <button class="boton" data-accion="nueva-general">+ Agregar promoción</button>
        </div>
        <div id="nueva-general"></div>
        <div class="lista-promos">${generales.map((g) => tarjetaGeneral(g, abierta === `g${g.id}`)).join("")}</div>
      </section>
      <section class="seccion-promos">
        <div class="promos-cabecera">
          <div>
            <h1>Beneficios del club</h1>
            <p>Lo que gana cada cliente según sus visitas. El programa calcula el descuento solo. Prendé las que quieras usar y tocá «Cambiar» para elegir porcentajes, techos y pisos.</p>
          </div>
          <button class="boton" data-accion="nueva-promo">+ Agregar beneficio</button>
        </div>
        <div id="nueva"></div>
        <div class="lista-promos">${promos.map((p) => tarjetaPromo(p, mecanismos, abierta === p.id)).join("")}</div>
      </section>
      <section class="seccion-promos">
        <div class="promos-cabecera">
          <div>
            <h1>Solo para el negocio</h1>
            <p>Esto tiene datos personales: abrilo cuando el cliente no esté mirando la pantalla.</p>
          </div>
        </div>
        <div class="lista-promos">
          <article class="promo prendida"><div class="promo-fila">
            <div class="promo-texto"><h2>Clientes</h2><p>La lista de clientes y el perfil de cada uno, con sus datos, su estado y sus compras.</p></div>
            <button class="boton" data-accion="ir-clientes">Ver clientes</button>
          </div></article>
          <article class="promo prendida"><div class="promo-fila">
            <div class="promo-texto"><h2>Movimientos</h2><p>Todas las visitas registradas, para corregir errores o cargar una que quedó sin registrar.</p></div>
            <button class="boton" data-accion="ir-movimientos">Ver movimientos</button>
          </div></article>
        </div>
      </section>`, { promos, mecanismos, generales });
    const form = document.querySelector('[data-form="promo"], [data-form="general"]');
    if (form) {
      if (form.dataset.form === "promo") ajustarEditor(form);
      form.scrollIntoView({ block: "center" });
    }
  } catch (e) {
    avisar(e.message, true);
  }
}

const interruptor = (accion, id, nombre, activa) => `
  <button class="interruptor ${activa ? "prendido" : ""}" data-accion="${accion}" data-id="${id}"
    role="switch" aria-checked="${activa}" aria-label="${esc(nombre)}"><i></i>${activa ? "Prendida" : "Apagada"}</button>`;

function tarjetaGeneral(g, abierta) {
  const fechas = [g.desde && `desde el ${fechaCorta(g.desde)}`, g.hasta && `hasta el ${fechaCorta(g.hasta)}`].filter(Boolean).join(" ");
  return `
    <article class="promo ${g.activa ? "prendida" : ""}">
      <div class="promo-fila">
        ${circuloGeneral(g)}
        <div class="promo-texto">
          <h2>${esc(g.nombre)}</h2>
          <p>${esc(g.descripcion)}</p>
          <p class="ayuda">${esc(g.texto_dias)}${fechas ? ", " + esc(fechas) : ""}</p>
        </div>
        <div class="promo-botones">
          ${interruptor("alternar-general", g.id, g.nombre, g.activa)}
          <button class="boton" data-accion="editar-general" data-id="${g.id}">Cambiar</button>
        </div>
      </div>
      ${abierta ? editorGeneral(g) : ""}
    </article>`;
}

const fechaCorta = (iso) => iso.split("-").reverse().join("/");

function editorGeneral(g) {
  return `
    <form class="editor" data-form="general" data-id="${g.id ?? ""}" data-activa="${g.activa ? 1 : ""}">
      <label class="campo"><span>Nombre de la promoción</span>
        <input name="nombre" value="${esc(g.nombre)}" required></label>
      <label class="campo"><span>¿De qué se trata?</span>
        <input name="descripcion" value="${esc(g.descripcion)}" placeholder="Ejemplo: llevando 2 kilos, el kilo a precio promocional"></label>
      <fieldset class="grupo"><legend>¿Qué ícono lleva?</legend><div class="opciones">
        ${Object.entries(ICONOS_GENERALES).map(([clave, i]) => `<label class="opcion"><input type="radio" name="icono" value="${clave}" ${(g.icono ?? "general") === clave ? "checked" : ""}>${i.html}${i.texto}</label>`).join("")}
      </div></fieldset>
      <fieldset class="grupo"><legend>¿Qué días vale?</legend><div class="opciones">
        ${DIAS.map((d, i) => `<label class="opcion"><input type="checkbox" name="dias" value="${i}" ${g.dias.includes(i) ? "checked" : ""}>${d}</label>`).join("")}
      </div></fieldset>
      <div class="dos-campos">
        <label class="campo"><span>Vale desde (opcional)</span><input type="date" name="desde" value="${esc(g.desde)}"></label>
        <label class="campo"><span>Vale hasta (opcional)</span><input type="date" name="hasta" value="${esc(g.hasta)}"></label>
      </div>
      <p class="mensaje-error" data-error role="alert"></p>
      <div class="acciones">
        <button class="boton principal" type="submit">Guardar</button>
        <button class="boton" type="button" data-accion="ir-promos">Cancelar</button>
        ${g.id ? `<button class="boton discreto" type="button" data-accion="borrar-general" data-id="${g.id}">Borrar esta promoción</button>` : ""}
      </div>
    </form>`;
}

async function guardarGeneral(form) {
  const f = new FormData(form);
  const datos = {
    nombre: f.get("nombre"),
    descripcion: f.get("descripcion"),
    activa: Boolean(form.dataset.activa),
    dias: f.getAll("dias").map(Number),
    icono: f.get("icono"),
    desde: f.get("desde"),
    hasta: f.get("hasta"),
  };
  try {
    const guardada = form.dataset.id
      ? await api(`/api/generales/${form.dataset.id}`, "PUT", datos)
      : await api("/api/generales", "POST", datos);
    avisar(`«${guardada.nombre}» guardada.`);
    irPromos();
  } catch (e) {
    form.querySelector("[data-error]").textContent = e.message;
  }
}

async function alternarGeneral(id) {
  const g = estado.generales.find((x) => x.id === id);
  try {
    await api(`/api/generales/${id}`, "PUT", { ...g, activa: !g.activa });
    avisar(`«${g.nombre}» ${g.activa ? "apagada" : "prendida"}.`);
    irPromos();
  } catch (e) {
    avisar(e.message, true);
  }
}

async function borrarGeneral(id) {
  const g = estado.generales.find((x) => x.id === id);
  if (!confirm(`¿Seguro que querés borrar «${g.nombre}»? Si solo querés pausarla, apagala.`)) return;
  try {
    await api(`/api/generales/${id}`, "DELETE");
    avisar(`«${g.nombre}» borrada.`);
    irPromos();
  } catch (e) {
    avisar(e.message, true);
  }
}

function nuevaGeneral() {
  const zona = document.getElementById("nueva-general");
  zona.innerHTML = `<section class="tarjeta nueva"><h2>Nueva promoción para todos</h2>${editorGeneral({
    nombre: "", descripcion: "", activa: true, dias: [0, 1, 2, 3, 4, 5, 6], desde: "", hasta: "",
  })}</section>`;
  zona.querySelector('[name="nombre"]').focus();
}

function tarjetaPromo(p, mecanismos, abierta) {
  const m = mecanismos[p.tipo];
  return `
    <article class="promo ${p.activa ? "prendida" : ""}">
      <div class="promo-fila">
        ${circulo(p.tipo)}
        <div class="promo-texto">
          <h2>${esc(p.nombre)}</h2>
          <p>${esc(p.descripcion)}</p>
          <p class="ayuda">${esc(m.ayuda)}</p>
        </div>
        <div class="promo-botones">
          ${interruptor("alternar-promo", p.id, p.nombre, p.activa)}
          <button class="boton" data-accion="editar-promo" data-id="${p.id}">Cambiar</button>
        </div>
      </div>
      ${abierta ? editorPromo(p, m) : ""}
    </article>`;
}

function campoMecanismo(c, valor) {
  if (c.tipo === "numero") {
    return `<label class="campo"><span>${esc(c.etiqueta)}</span>
      <input type="number" min="${c.minimo ?? 1}" name="param_${c.clave}" value="${esc(valor)}" required></label>`;
  }
  if (c.tipo === "dias") {
    return `<fieldset class="grupo"><legend>${esc(c.etiqueta)}</legend><div class="opciones">
      ${DIAS.map((d, i) => `<label class="opcion"><input type="checkbox" name="param_dias" value="${i}" ${valor.includes(i) ? "checked" : ""}>${d}</label>`).join("")}
      </div></fieldset>`;
  }
  return `<label class="opcion acepta"><input type="checkbox" name="param_${c.clave}" ${valor ? "checked" : ""}>${esc(c.etiqueta)}</label>`;
}

function editorPromo(p, m) {
  const opcion = (valor, texto) => `<label class="opcion">
    <input type="radio" name="beneficio" value="${valor}" ${p.beneficio === valor ? "checked" : ""}>${texto}</label>`;
  const campos = m.campos.map((c) => campoMecanismo(c, p.params[c.clave] ?? c.defecto)).join("");
  return `
    <form class="editor" data-form="promo" data-id="${p.id ?? ""}" data-tipo="${p.tipo}" data-activa="${p.activa ? 1 : ""}">
      <label class="campo"><span>Nombre del beneficio</span>
        <input name="nombre" value="${esc(p.nombre)}" required></label>
      ${campos}
      <fieldset class="grupo"><legend>¿Qué se lleva el cliente?</legend>
        <div class="opciones">
          ${opcion("porcentaje", "Un % de descuento")}
          ${opcion("monto", "Pesos de descuento")}
          ${opcion("regalo", "Un regalo")}
        </div>
      </fieldset>
      <div class="dos-campos">
        <label class="campo" data-solo="porcentaje monto"><span>¿Cuánto? (% o pesos)</span>
          <input type="number" step="any" min="0" name="valor" value="${p.valor || ""}"></label>
        <label class="campo" data-solo="regalo"><span>¿Qué regalo?</span>
          <input name="regalo" value="${esc(p.regalo)}" placeholder="Ejemplo: un chimichurri"></label>
        <label class="campo" data-solo="porcentaje"><span>Descuento máximo en pesos (techo)</span>
          <small>Dejalo vacío si no querés tope.</small>
          <input type="number" min="0" name="techo" value="${p.techo || ""}"></label>
        <label class="campo"><span>Compra mínima en pesos (piso)</span>
          <small>Dejalo vacío si vale para cualquier compra.</small>
          <input type="number" min="0" name="piso" value="${p.piso || ""}"></label>
      </div>
      <div class="dos-campos">
        <label class="campo"><span>Vale desde (opcional)</span><input type="date" name="desde" value="${esc(p.desde)}"></label>
        <label class="campo"><span>Vale hasta (opcional)</span><input type="date" name="hasta" value="${esc(p.hasta)}"></label>
      </div>
      <p class="mensaje-error" data-error role="alert"></p>
      <div class="acciones">
        <button class="boton principal" type="submit">Guardar</button>
        <button class="boton" type="button" data-accion="ir-promos">Cancelar</button>
      </div>
    </form>`;
}

function ajustarEditor(form) {
  const beneficio = form.elements.beneficio.value;
  form.querySelectorAll("[data-solo]").forEach((c) => {
    c.hidden = !c.dataset.solo.split(" ").includes(beneficio);
  });
}

function leerEditor(form) {
  const m = estado.mecanismos[form.dataset.tipo];
  const params = {};
  for (const c of m.campos) {
    if (c.tipo === "numero") params[c.clave] = Number(form.elements[`param_${c.clave}`].value);
    else if (c.tipo === "dias") params[c.clave] = [...form.querySelectorAll('[name="param_dias"]:checked')].map((i) => Number(i.value));
    else params[c.clave] = form.elements[`param_${c.clave}`].checked;
  }
  const f = new FormData(form);
  return {
    nombre: f.get("nombre"),
    tipo: form.dataset.tipo,
    activa: Boolean(form.dataset.activa),
    beneficio: f.get("beneficio"),
    valor: f.get("valor") || 0,
    regalo: f.get("regalo"),
    piso: f.get("piso"),
    techo: f.get("techo"),
    desde: f.get("desde"),
    hasta: f.get("hasta"),
    params,
  };
}

async function guardarPromo(form) {
  try {
    const datos = leerEditor(form);
    const guardada = form.dataset.id
      ? await api(`/api/promos/${form.dataset.id}`, "PUT", datos)
      : await api("/api/promos", "POST", datos);
    avisar(`«${guardada.nombre}» guardada.`);
    irPromos();
  } catch (e) {
    form.querySelector("[data-error]").textContent = e.message;
  }
}

async function alternarPromo(id) {
  const promo = estado.promos.find((p) => p.id === id);
  try {
    await api(`/api/promos/${id}`, "PUT", { ...promo, activa: !promo.activa });
    avisar(`«${promo.nombre}» ${promo.activa ? "apagada" : "prendida"}.`);
    irPromos();
  } catch (e) {
    // Una promo guardada sin datos completos no se puede prender: se abre para completarla.
    avisar(e.message, true);
    irPromos(id);
  }
}

function mostrarNuevaPromo() {
  document.getElementById("nueva").innerHTML = `
    <section class="tarjeta nueva">
      <h2>¿Qué tipo de beneficio querés agregar?</h2>
      <div class="nueva-lista">
        ${Object.entries(estado.mecanismos).map(([tipo, m]) => `
          <button data-accion="elegir-mecanismo" data-tipo="${tipo}">
            <b>${esc(m.nombre)}</b><small>${esc(m.ayuda)}</small>
          </button>`).join("")}
      </div>
    </section>`;
}

function elegirMecanismo(tipo) {
  const m = estado.mecanismos[tipo];
  const params = Object.fromEntries(m.campos.map((c) => [c.clave, c.defecto]));
  const borrador = { nombre: m.nombre, tipo, activa: true, beneficio: "porcentaje", valor: 10, regalo: "", piso: 0, techo: 0, desde: "", hasta: "", params };
  const zona = document.getElementById("nueva");
  zona.innerHTML = `<section class="tarjeta nueva"><h2>Nuevo beneficio: ${esc(m.nombre)}</h2><p>${esc(m.ayuda)}</p>${editorPromo(borrador, m)}</section>`;
  const form = zona.querySelector("form");
  ajustarEditor(form);
  form.elements.nombre.focus();
}

// Eventos

const acciones = {
  "ir-inicio": () => irInicio(),
  "ir-promos": () => irPromos(),
  "ir-movimientos": () => {
    filtros = { ...FILTROS_VACIOS };
    return irMovimientos();
  },
  "volver-movimientos": () => alVolver(),
  "mas-movimientos": () => {
    filtros.limite += FILTROS_VACIOS.limite;
    return irMovimientos();
  },
  "nuevo-movimiento": () => irFormularioMovimiento(null),
  "editar-movimiento": (b) => irFormularioMovimiento(estado.movimientos.find((m) => m.id === Number(b.dataset.visita))),
  "recuperar": (b) => recuperar(Number(b.dataset.visita)),
  "ir-alta": (b) => irFormularioCliente(null, b.dataset.dni ?? digitos(document.getElementById("entrada")?.value ?? "")),
  "editar-cliente": () => irFormularioCliente(estado.perfil.cliente),
  "ir-clientes": () => {
    filtrosClientes = { ...FILTROS_CLIENTES_VACIOS };
    return irClientes();
  },
  "ir-clientes-volver": () => irClientes(),
  "mas-clientes": () => {
    filtrosClientes.limite += FILTROS_CLIENTES_VACIOS.limite;
    return irClientes();
  },
  "ver-perfil": (b) => irPerfil(b.dataset.dni),
  "movimientos-de": (b) => {
    filtros = { ...FILTROS_VACIOS, texto: b.dataset.dni };
    return irMovimientos();
  },
  "nuevo-movimiento-de": (b) => irFormularioMovimiento(null, b.dataset.dni),
  "sumar-visita": () => sumarVisita(),
  "volver-ficha": () => irFicha(estado.ficha),
  "confirmar": () => confirmarVisita(estado.ficha, estado.monto),
  "corregir-monto": () => irMonto(estado.ficha, estado.candidatas),
  "anular": (b) => anular(Number(b.dataset.visita)),
  "alternar-promo": (b) => alternarPromo(Number(b.dataset.id)),
  "editar-promo": (b) => irPromos(Number(b.dataset.id)),
  "nueva-promo": () => mostrarNuevaPromo(),
  "elegir-mecanismo": (b) => elegirMecanismo(b.dataset.tipo),
  "alternar-general": (b) => alternarGeneral(Number(b.dataset.id)),
  "editar-general": (b) => irPromos(`g${b.dataset.id}`),
  "borrar-general": (b) => borrarGeneral(Number(b.dataset.id)),
  "nueva-general": () => nuevaGeneral(),
};

const formularios = {
  dni: buscarDni,
  monto: calcular,
  general: guardarGeneral,
  promo: guardarPromo,
  movimiento: guardarMovimiento,
  "filtro-movimientos": filtrarMovimientos,
  "filtro-clientes": filtrarClientes,
};

// Evita doble registro si alguien toca dos veces el mismo botón.
let ocupado = false;

document.addEventListener("click", async (e) => {
  const boton = e.target.closest("[data-accion]");
  if (!boton || ocupado) return;
  ocupado = true;
  try {
    await acciones[boton.dataset.accion](boton);
  } finally {
    ocupado = false;
  }
});

document.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (ocupado) return;
  ocupado = true;
  try {
    if (e.target.id === "form-cliente") await guardarCliente(e.target);
    else await formularios[e.target.dataset.form]?.(e.target);
  } finally {
    ocupado = false;
  }
});

document.addEventListener("change", (e) => {
  if (e.target.name === "beneficio") ajustarEditor(e.target.form);
});

// Los campos numéricos solo aceptan números y los muestran con puntos.
document.addEventListener("input", (e) => {
  if (e.target.form?.dataset.form === "movimiento") actualizarCobrado(e.target.form);
  if (!("numero" in e.target.dataset)) return;
  e.target.value = conPuntos(digitos(e.target.value).slice(0, Number(e.target.dataset.maximo)));
  const error = document.getElementById("error");
  if (error) error.textContent = "";
});

document.addEventListener("keydown", (e) => {
  reiniciarTemporizador();
  // Mantener apretado Enter no tiene que saltear pantallas.
  if (e.key === "Enter" && e.repeat) return e.preventDefault();
  if (e.key === "Escape" && ["ficha", "no-encontrado", "resultado"].includes(estado.vista)) return irInicio();
  // Aunque hayan hecho clic en otro lado, escribir un número siempre va al campo.
  if (/^[0-9]$/.test(e.key) && !e.target.matches("input, select, textarea")) {
    document.getElementById("entrada")?.focus();
  }
});
document.addEventListener("pointerdown", reiniciarTemporizador);
document.addEventListener("wheel", reiniciarTemporizador, { passive: true });

irInicio();
