const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const {test} = require("node:test");

function entorno() {
    const eventos = {};
    const boton = {disabled: false};
    const cancelar = {hidden: true, addEventListener: (nombre, fn) => eventos.cancelar = fn};
    const formulario = {querySelector: () => boton, append() {}, addEventListener: (nombre, fn) => eventos.submit = fn};
    const estado = {};
    const resultados = {};
    const entrada = {texto: "RESERVAR L025 U104 7;", archivo: {size: 20}};
    const contexto = {
        window: {BIBLIOTECA_API: "http://127.0.0.1:5000"},
        document: {querySelector: () => formulario, createElement: () => cancelar, getElementById: id => id === "resultados" ? resultados : estado},
        FormData: class {get(nombre) {return entrada[nombre];}},
        inicializarResultados() {contexto.inicializado = true;},
        AbortController, DOMException, setTimeout, clearTimeout, Date,
        fetch: async () => ({ok: true, headers: {get: () => "application/json"}, json: async () => ({status: "ok", html: "<svg></svg>"})})
    };
    vm.createContext(contexto);
    vm.runInContext(fs.readFileSync("netlify-public/cliente.js", "utf8"), contexto);
    return {contexto, eventos, boton, cancelar, estado, resultados, entrada};
}

test("Reintenta errores de red y HTML de reactivación hasta recibir salud JSON", async () => {
    const {contexto} = entorno();
    let reloj = 0;
    let solicitudes = 0;
    contexto.Date = {now: () => reloj};
    contexto.pausa = async ms => reloj += ms;
    contexto.fetch = async () => {
        solicitudes++;
        if (solicitudes === 1) throw new TypeError("Network error");
        return {ok: true, headers: {get: () => solicitudes === 2 ? "text/html" : "application/json"}, json: async () => ({status: "ok"})};
    };
    await contexto.esperarServidor("http://127.0.0.1:5000", new AbortController().signal, () => {}, 10000);
    assert.equal(solicitudes, 3);
});

test("La espera total termina y no deja un sondeo periódico", async () => {
    const {contexto} = entorno();
    let reloj = 0;
    contexto.Date = {now: () => reloj};
    contexto.pausa = async ms => reloj += ms;
    contexto.fetch = async () => {throw new TypeError("Offline");};
    await assert.rejects(contexto.esperarServidor("http://127.0.0.1:5000", new AbortController().signal, () => {}, 3000), /entrada se conserva/);
    assert.equal(reloj, 3000);
});

test("Timeout de una solicitud cancela fetch", async () => {
    const {contexto} = entorno();
    contexto.fetch = (url, opciones) => new Promise((resolve, reject) => opciones.signal.addEventListener("abort", () => reject(new DOMException("Timeout", "AbortError"))));
    await assert.rejects(contexto.fetchConLimite("/healthz", {}, 5, new AbortController().signal), {name: "AbortError"});
});

test("POST multipart directo presenta el resultado y activa el zoom", async () => {
    const {contexto, eventos, boton, estado, resultados} = entorno();
    contexto.esperarServidor = async () => {};
    let enviada;
    contexto.fetch = async (url, opciones) => {
        enviada = {url, opciones};
        return {ok: true, headers: {get: () => "application/json"}, json: async () => ({html: "<svg></svg>"})};
    };
    await eventos.submit({preventDefault() {}});
    assert.equal(enviada.url, "http://127.0.0.1:5000/api/analizar");
    assert.equal(enviada.opciones.method, "POST");
    assert.equal(enviada.opciones.body.get("texto"), "RESERVAR L025 U104 7;");
    assert.equal(enviada.opciones.headers, undefined);
    assert.equal(resultados.innerHTML, "<svg></svg>");
    assert.equal(contexto.inicializado, true);
    assert.equal(boton.disabled, false);
    assert.equal(estado.textContent, "Análisis completado.");
});

test("Cancelar conserva entrada y habilita un nuevo intento", async () => {
    const {contexto, eventos, entrada, boton, estado, cancelar} = entorno();
    contexto.esperarServidor = (url, signal) => new Promise((resolve, reject) => signal.addEventListener("abort", () => reject(new DOMException("Cancelado", "AbortError"))));
    const pendiente = eventos.submit({preventDefault() {}});
    eventos.cancelar();
    await pendiente;
    assert.equal(entrada.texto, "RESERVAR L025 U104 7;");
    assert.equal(entrada.archivo.size, 20);
    assert.equal(boton.disabled, false);
    assert.equal(cancelar.hidden, true);
    assert.match(estado.textContent, /cancelada/);
});

test("Errores de validación y Graphviz se presentan sin perder la entrada", async () => {
    for (const status of [400, 413, 503]) {
        const {contexto, eventos, estado, boton, entrada} = entorno();
        contexto.esperarServidor = async () => {};
        contexto.fetch = async () => ({ok: false, status, headers: {get: () => "application/json"}, json: async () => ({mensaje: "Error de prueba"})});
        await eventos.submit({preventDefault() {}});
        assert.equal(estado.textContent, "Error de prueba");
        assert.equal(boton.disabled, false);
        assert.equal(entrada.archivo.size, 20);
    }
});

test("El marcador de configuración no inicia peticiones", async () => {
    const {contexto, eventos, estado} = entorno();
    contexto.window.BIBLIOTECA_API = "https://REEMPLAZAR.invalid";
    contexto.fetch = () => {throw new Error("No solicitar");};
    await eventos.submit({preventDefault() {}});
    assert.match(estado.textContent, /Falta configurar/);
});

test("Los controles originales funcionan al inicializar resultados nuevos", () => {
    const imagen = {dataset: {}, style: {}, viewBox: {baseVal: {width: 1000, height: 200}}};
    const grafico = {id: "grafico-prueba", scrollLeft: 70, scrollTop: 10, querySelector: () => imagen};
    const clases = new Set();
    const panel = {classList: {add: v => clases.add(v), remove: v => clases.delete(v)}};
    const boton = {dataset: {token: "DIAS"}, classList: panel.classList};
    const contexto = {document: {
        querySelectorAll: selector => selector === ".grafico" ? [grafico] : selector === ".boton-token" ? [boton] : [panel],
        querySelector: () => boton,
        getElementById: id => id === grafico.id ? grafico : panel
    }};
    vm.createContext(contexto);
    const script = fs.readFileSync("templates/index.html", "utf8").split("<script>")[1].split("</script>")[0];
    vm.runInContext(script, contexto);
    assert.equal(imagen.style.width, "1000px");
    assert.equal(clases.has("activo"), true);
    contexto.cambiarZoom(grafico.id, 1.25);
    assert.equal(imagen.style.width, "1250px");
    contexto.cambiarZoom(grafico.id, 0.8);
    assert.equal(imagen.style.width, "1000px");
    contexto.inicializarResultados();
    assert.equal(imagen.dataset.escala, 1);
    assert.equal(grafico.scrollLeft, 0);
});
