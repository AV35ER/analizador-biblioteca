
import os
import re
from graphviz import ExecutableNotFound, CalledProcessError
from flask import Flask, abort, render_template, request
from automatas import EXPRESIONES, generar_todos, obtener_alfabeto

app = Flask(__name__)
LIMITE_ENTRADA = 1024 * 1024
app.config.update(
    MAX_CONTENT_LENGTH=2 * LIMITE_ENTRADA + 64 * 1024,
    MAX_FORM_MEMORY_SIZE=LIMITE_ENTRADA + 64 * 1024,
    MAX_FORM_PARTS=10
)

REGLAS = [
    (nombre, re.compile(patron))
    for nombre, patron in EXPRESIONES.items()
]

EJEMPLO = "RESERVAR L025 U104 7;"


def obtener_automatas(nombres=None):
    return generar_todos(nombres)


def analizar(texto):
    tokens = []
    errores = []

    for numero, linea in enumerate(texto.splitlines(), start=1):
        coincidencias = re.finditer(r";|[^\s;]+", linea)

        for coincidencia in coincidencias:
            lexema = coincidencia.group()

            elemento = {
                "linea": numero,
                "columna": coincidencia.start() + 1,
                "lexema": lexema
            }

            for nombre, patron in REGLAS:
                if patron.fullmatch(lexema):
                    tokens.append({
                        **elemento,
                        "token": nombre
                    })
                    break
            else:
                errores.append(elemento)

    return tokens, errores


def preparar_tabla(automata, es_afnd):
    alfabeto = obtener_alfabeto(automata)

    if es_afnd:
        alfabeto = alfabeto + ["ε"]

    filas = []

    for estado in automata["estados"]:
        destinos = {}

        for simbolo in alfabeto:
            encontrados = set()

            for transicion in automata["transiciones"]:
                if transicion["origen"] != estado:
                    continue

                valor = transicion["simbolo"]

                if valor == simbolo:
                    encontrados.add(transicion["destino"])
                elif valor == "[0-9]" and simbolo in "0123456789":
                    encontrados.add(transicion["destino"])
                elif valor == "[1-9]" and simbolo in "123456789":
                    encontrados.add(transicion["destino"])

            destinos[simbolo] = ", ".join(
                sorted(
                    encontrados,
                    key=lambda x: (x[0], int(x[1:]))
                )
            ) if encontrados else "∅"

        filas.append({
            "estado": estado,
            "inicial": estado == automata["inicial"],
            "final": estado in automata["finales"],
            "destinos": destinos
        })

    return {
        "alfabeto": alfabeto,
        "filas": filas
    }


def preparar_resultados(tokens):
    nombres = list(dict.fromkeys(t["token"] for t in tokens))
    automatas = obtener_automatas(nombres)
    resultados = {}

    for nombre in nombres:
        datos = automatas[nombre]

        resultados[nombre] = {
            **datos,
            "tabla_visual_afnd": preparar_tabla(datos["afnd"], True),
            "tabla_visual_afd": preparar_tabla(datos["afd"], False)
        }

    return resultados


@app.route("/", methods=["GET", "POST"])
@app.route("/api/analizar", methods=["POST"])
def inicio():
    texto = EJEMPLO
    tokens = []
    errores = []
    mensaje = ""
    analizado = False
    resultados = {}

    if request.method == "POST":
        texto = request.form.get("texto", "")
        archivo = request.files.get("archivo")

        if archivo and archivo.filename:
            if not archivo.filename.lower().endswith(".txt"):
                mensaje = "Selecciona un archivo TXT."
            else:
                try:
                    contenido = archivo.read(LIMITE_ENTRADA + 1)
                    if len(contenido) > LIMITE_ENTRADA:
                        abort(413)
                    texto = contenido.decode("utf-8-sig")
                except UnicodeDecodeError:
                    mensaje = "El archivo debe estar guardado en UTF-8."

        if not mensaje:
            if len(texto.encode("utf-8")) > LIMITE_ENTRADA:
                abort(413)
            if texto.strip():
                tokens, errores = analizar(texto)
                analizado = True
                try:
                    resultados = preparar_resultados(tokens)
                except (ExecutableNotFound, CalledProcessError):
                    mensaje = (
                        "No se pudieron generar los gráficos. Comprueba que Graphviz "
                        "esté instalado y que el comando dot esté disponible en PATH."
                    )
            else:
                mensaje = "Escribe una instruccion o carga un archivo."

    if request.path == "/api/analizar":
        return {
            "html": render_template(
                "resultados.html", tokens=tokens, errores=errores,
                analizado=analizado, resultados=resultados
            ),
            "mensaje": mensaje,
            "texto": texto,
            "tokens": tokens,
            "errores": errores
        }, 503 if analizado and mensaje else 400 if mensaje else 200

    return render_template(
        "index.html",
        texto=texto,
        tokens=tokens,
        errores=errores,
        mensaje=mensaje,
        analizado=analizado,
        resultados=resultados,
        expresiones=EXPRESIONES
    )


@app.get("/healthz")
def salud():
    return {"status": "ok"}


@app.after_request
def configurar_cache(respuesta):
    if request.endpoint != "static":
        respuesta.headers["Cache-Control"] = "no-store"
    origen = request.headers.get("Origin")
    permitidos = {valor.strip() for valor in os.environ.get("CORS_ORIGINS", "").split(",") if valor.strip()}
    if request.path in ("/api/analizar", "/healthz"):
        respuesta.vary.add("Origin")
        if origen in permitidos:
            respuesta.headers["Access-Control-Allow-Origin"] = origen
            respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return respuesta


@app.errorhandler(413)
def archivo_grande(error):
    if request.path == "/api/analizar":
        return {"mensaje": "La entrada supera el máximo de 1 MiB."}, 413
    return "El archivo supera el maximo de 1 MB.", 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
