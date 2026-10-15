
from functools import lru_cache
from collections import deque
from graphviz import Digraph

EXPRESIONES = {
    "ACCION": "RESERVAR",
    "CODIGO_LIBRO": "L[0-9]{3}",
    "CODIGO_USUARIO": "U[0-9]{3}",
    "DIAS": "[1-9][0-9]*",
    "FIN_INSTRUCCION": ";"
}


def expandir_simbolo(simbolo):
    if simbolo == "[0-9]":
        return list("0123456789")
    if simbolo == "[1-9]":
        return list("123456789")
    if simbolo == "ε":
        return []
    return [simbolo]


class GeneradorAFND:
    def __init__(self):
        self.estados = []
        self.transiciones = []

    def nuevo_estado(self):
        estado = "q" + str(len(self.estados))
        self.estados.append(estado)
        return estado

    def conectar(self, origen, simbolo, destino):
        self.transiciones.append({
            "origen": origen,
            "simbolo": simbolo,
            "destino": destino
        })

    def simbolo(self, valor):
        inicio = self.nuevo_estado()
        fin = self.nuevo_estado()
        self.conectar(inicio, valor, fin)
        return inicio, fin

    def concatenar(self, a, b):
        self.conectar(a[1], "ε", b[0])
        return a[0], b[1]

    def estrella(self, fragmento):
        inicio = self.nuevo_estado()
        fin = self.nuevo_estado()

        self.conectar(inicio, "ε", fragmento[0])
        self.conectar(inicio, "ε", fin)
        self.conectar(fragmento[1], "ε", fragmento[0])
        self.conectar(fragmento[1], "ε", fin)

        return inicio, fin

    def construir(self, expresion):
        partes = []
        i = 0

        while i < len(expresion):
            if expresion[i] == "[":
                fin = expresion.index("]", i)
                valor = expresion[i:fin + 1]

                if valor not in ("[0-9]", "[1-9]"):
                    raise ValueError("Rango no soportado")

                i = fin + 1
            else:
                valor = expresion[i]
                i += 1

            cantidad = 1
            repetir = False

            if i < len(expresion) and expresion[i] == "{":
                fin = expresion.index("}", i)
                cantidad = int(expresion[i + 1:fin])
                i = fin + 1

            if i < len(expresion) and expresion[i] == "*":
                repetir = True
                i += 1

            if repetir:
                partes.append(self.estrella(self.simbolo(valor)))
            else:
                for _ in range(cantidad):
                    partes.append(self.simbolo(valor))

        if not partes:
            raise ValueError("Expresion vacia")

        resultado = partes[0]

        for parte in partes[1:]:
            resultado = self.concatenar(resultado, parte)

        return {
            "estados": self.estados,
            "inicial": resultado[0],
            "finales": [resultado[1]],
            "transiciones": self.transiciones
        }


def crear_afnd(expresion):
    return GeneradorAFND().construir(expresion)


def obtener_alfabeto(automata):
    simbolos = set()

    for t in automata["transiciones"]:
        simbolos.update(expandir_simbolo(t["simbolo"]))

    return sorted(simbolos)


def cierre_epsilon(estados, transiciones):
    cierre = set(estados)
    pendientes = list(estados)

    while pendientes:
        actual = pendientes.pop()

        for t in transiciones:
            if t["origen"] == actual and t["simbolo"] == "ε":
                destino = t["destino"]

                if destino not in cierre:
                    cierre.add(destino)
                    pendientes.append(destino)

    return frozenset(cierre)


def mover(estados, simbolo, transiciones):
    destinos = set()

    for t in transiciones:
        if t["origen"] in estados:
            if simbolo in expandir_simbolo(t["simbolo"]):
                destinos.add(t["destino"])

    return destinos


def convertir_afd(afnd):
    transiciones = afnd["transiciones"]
    alfabeto = obtener_alfabeto(afnd)

    inicial = cierre_epsilon(
        [afnd["inicial"]],
        transiciones
    )

    conjuntos = {inicial: "D0"}
    pendientes = deque([inicial])

    estados = ["D0"]
    finales = []
    nuevas_transiciones = []
    equivalencias = {}

    while pendientes:
        conjunto = pendientes.popleft()
        nombre = conjuntos[conjunto]

        equivalencias[nombre] = sorted(
            conjunto,
            key=lambda x: int(x[1:])
        )

        if any(e in afnd["finales"] for e in conjunto):
            finales.append(nombre)

        for simbolo in alfabeto:
            destinos = mover(
                conjunto,
                simbolo,
                transiciones
            )

            cierre = cierre_epsilon(
                destinos,
                transiciones
            )

            if cierre not in conjuntos:
                nuevo = "D" + str(len(conjuntos))
                conjuntos[cierre] = nuevo
                estados.append(nuevo)
                pendientes.append(cierre)

            nuevas_transiciones.append({
                "origen": nombre,
                "simbolo": simbolo,
                "destino": conjuntos[cierre]
            })

    return {
        "estados": estados,
        "inicial": "D0",
        "finales": finales,
        "transiciones": nuevas_transiciones,
        "equivalencias": equivalencias
    }


def generar_quintupla(automata):
    return {
        "Q": automata["estados"],
        "Sigma": obtener_alfabeto(automata),
        "delta": automata["transiciones"],
        "q0": automata["inicial"],
        "F": automata["finales"]
    }


def generar_tabla(automata):
    alfabeto = obtener_alfabeto(automata)
    if any(t["simbolo"] == "ε" for t in automata["transiciones"]):
        alfabeto.append("ε")
    tabla = []

    for estado in automata["estados"]:
        fila = {"estado": estado}

        for simbolo in alfabeto:
            destinos = set()

            for t in automata["transiciones"]:
                if t["origen"] == estado:
                    if simbolo == t["simbolo"] or simbolo in expandir_simbolo(t["simbolo"]):
                        destinos.add(t["destino"])

            fila[simbolo] = sorted(destinos) if destinos else []

        tabla.append(fila)

    return tabla


def dibujar_automata(automata, ruta=None, titulo="", formato="svg"):
    grafo = Digraph(format=formato)

    grafo.attr(
        rankdir="LR",
        label=titulo,
        labelloc="t",
        fontsize="18"
    )

    grafo.node("inicio", shape="point")

    for estado in automata["estados"]:
        forma = "doublecircle" if estado in automata["finales"] else "circle"
        grafo.node(estado, shape=forma)

    grafo.edge("inicio", automata["inicial"])

    for t in automata["transiciones"]:
        grafo.edge(
            t["origen"],
            t["destino"],
            label=t["simbolo"]
        )

    contenido = grafo.pipe(format=formato)
    if formato == "svg":
        return "<svg" + contenido.decode("utf-8").split("<svg", 1)[1]
    return contenido


@lru_cache(maxsize=32)
def generar_token(token, expresion):
    afnd = crear_afnd(expresion)
    afd = convertir_afd(afnd)
    return {
        "expresion": expresion,
        "afnd": afnd,
        "afd": afd,
        "quintupla_afnd": generar_quintupla(afnd),
        "quintupla_afd": generar_quintupla(afd),
        "tabla_afnd": generar_tabla(afnd),
        "tabla_afd": generar_tabla(afd),
        "imagen_afnd": dibujar_automata(afnd, titulo="AFND - " + token),
        "imagen_afd": dibujar_automata(afd, titulo="AFD - " + token)
    }


def generar_todos(nombres=None):
    if nombres is None:
        nombres = EXPRESIONES
    return {
        token: generar_token(token, EXPRESIONES[token])
        for token in nombres
    }


def generar_automata_accion():
    return generar_token("ACCION", EXPRESIONES["ACCION"])["imagen_afnd"]


if __name__ == "__main__":
    resultados = generar_todos()
    generar_automata_accion()

    for token, datos in resultados.items():
        print("\nTOKEN:", token)
        print("ER:", datos["expresion"])
        print("AFND:", len(datos["afnd"]["estados"]), "estados")
        print("AFD:", len(datos["afd"]["estados"]), "estados")
        print("Quintupla AFND:", datos["quintupla_afnd"])
        print("Quintupla AFD:", datos["quintupla_afd"])
        print("Tabla AFND:", datos["tabla_afnd"])
        print("Tabla AFD:", datos["tabla_afd"])
