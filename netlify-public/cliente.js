function pausa(ms, signal) {
    return new Promise((resolve, reject) => {
        const cancelar = () => {
            clearTimeout(timer);
            reject(new DOMException("Cancelado", "AbortError"));
        };
        if (signal.aborted) {
            reject(new DOMException("Cancelado", "AbortError"));
            return;
        }
        const timer = setTimeout(() => {
            signal.removeEventListener("abort", cancelar);
            resolve();
        }, ms);
        signal.addEventListener("abort", cancelar, {once: true});
    });
}

async function fetchConLimite(url, opciones, ms, signal) {
    const controlador = new AbortController();
    const cancelar = () => controlador.abort();
    if (signal.aborted) throw new DOMException("Cancelado", "AbortError");
    signal.addEventListener("abort", cancelar, {once: true});
    const timer = setTimeout(cancelar, ms);
    try {
        const respuesta = await fetch(url, {...opciones, signal: controlador.signal, credentials: "omit", cache: "no-store"});
        const tipo = respuesta.headers.get("content-type") || "";
        const datos = tipo.includes("application/json") ? await respuesta.json() : null;
        return {respuesta, datos};
    } finally {
        clearTimeout(timer);
        signal.removeEventListener("abort", cancelar);
    }
}

async function esperarServidor(origen, signal, avisar, limite = 180000) {
    const inicio = Date.now();
    while (Date.now() - inicio < limite) {
        avisar("Activando el servidor gratuito. Puede tardar unos minutos. Espera: " + Math.floor((Date.now() - inicio) / 1000) + " s.");
        try {
            const {respuesta, datos} = await fetchConLimite(origen + "/healthz", {}, Math.min(15000, limite - (Date.now() - inicio)), signal);
            if (respuesta.ok && datos && datos.status === "ok") return;
        } catch (error) {
            if (signal.aborted) throw error;
        }
        await pausa(Math.min(2000, Math.max(0, limite - (Date.now() - inicio))), signal);
    }
    throw new Error("El servidor todavía no responde. Tu entrada se conserva. Reintenta en unos minutos. Si persiste, revisa la URL de Render, CORS o los límites gratuitos.");
}

function conectarFormulario() {
    const formulario = document.querySelector("form");
    const estado = document.getElementById("estado-conexion");
    const compilar = formulario.querySelector('[type="submit"]');
    const cancelar = document.createElement("button");
    cancelar.type = "button";
    cancelar.textContent = "Cancelar espera";
    cancelar.hidden = true;
    formulario.append(cancelar);
    let controlador;
    cancelar.addEventListener("click", () => controlador.abort());
    const avisar = mensaje => {
        estado.hidden = false;
        estado.textContent = mensaje;
    };
    formulario.addEventListener("submit", async evento => {
        evento.preventDefault();
        if (compilar.disabled) return;
        const datosFormulario = new FormData(formulario);
        const archivo = datosFormulario.get("archivo");
        if (archivo && archivo.size > 1048576) {
            avisar("El archivo supera el máximo de 1 MiB.");
            return;
        }
        const origen = (window.BIBLIOTECA_API || "").replace(/\/$/, "");
        if (!/^https?:\/\//.test(origen) || origen.includes(".invalid")) {
            avisar("Falta configurar la URL real del servidor Render antes de publicar.");
            return;
        }
        controlador = new AbortController();
        compilar.disabled = true;
        cancelar.hidden = false;
        try {
            await esperarServidor(origen, controlador.signal, avisar);
            avisar("Analizando y generando los autómatas…");
            const {respuesta, datos} = await fetchConLimite(origen + "/api/analizar", {method: "POST", body: datosFormulario}, 90000, controlador.signal);
            if (datos && typeof datos.html === "string") {
                document.getElementById("resultados").innerHTML = datos.html;
                inicializarResultados();
            }
            if (!respuesta.ok) throw new Error(datos && datos.mensaje || "No se pudo completar el análisis. Reintenta; tu entrada se conserva.");
            if (!datos || typeof datos.html !== "string") throw new Error("Respuesta inesperada del servidor. Reintenta en unos minutos.");
            avisar(datos.mensaje || "Análisis completado.");
        } catch (error) {
            avisar(controlador.signal.aborted ? "Espera cancelada. Tu entrada se conserva." : error.name === "AbortError" ? "El análisis tardó demasiado. Tu entrada se conserva; puedes reintentar." : error.message || "No se pudo conectar. Reintenta en unos minutos.");
        } finally {
            compilar.disabled = false;
            cancelar.hidden = true;
        }
    });
}

conectarFormulario();
