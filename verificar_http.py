import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def solicitar(base, ruta="/", datos=None, tipo=None, origen=None, metodo=None):
    headers = {"Content-Type": tipo} if tipo else {}
    if origen:
        headers["Origin"] = origen
    peticion = Request(base.rstrip("/") + ruta, data=datos, headers=headers, method=metodo)
    try:
        with urlopen(peticion, timeout=25) as respuesta:
            return respuesta.status, respuesta.read(), respuesta.headers
    except HTTPError as error:
        return error.code, error.read(), error.headers


def verificar(base, origen=None):
    for intento in range(30):
        try:
            estado, cuerpo, _ = solicitar(base, "/healthz")
            if estado == 200 and json.loads(cuerpo) == {"status": "ok"}:
                break
        except (URLError, TimeoutError, ValueError):
            pass
        if intento == 29:
            raise RuntimeError("La aplicación no está disponible")
        time.sleep(2)

    estado, cuerpo, _ = solicitar(base)
    assert estado == 200 and b'<form method="POST"' in cuerpo
    datos = urlencode({"texto": "RESERVAR L025 U104 7;"}).encode()
    estado, cuerpo, headers = solicitar(base, datos=datos, tipo="application/x-www-form-urlencoded")
    assert estado == 200 and cuerpo.count(b"<svg") == 10
    assert b"static/img" not in cuerpo and headers["Cache-Control"] == "no-store"

    limite = "BibliotecaPruebaMultipart"
    contenido = (
        f"--{limite}\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"prueba.txt\"\r\n"
        "Content-Type: text/plain\r\n\r\nRESERVAR L025\nU104 7;\r\n"
        f"--{limite}--\r\n"
    ).encode()
    estado, cuerpo, _ = solicitar(base, datos=contenido, tipo="multipart/form-data; boundary=" + limite)
    assert estado == 200 and cuerpo.count(b"<svg") == 10
    estado, cuerpo, headers = solicitar(base, "/api/analizar", datos=contenido, tipo="multipart/form-data; boundary=" + limite, origen=origen)
    resultado = json.loads(cuerpo)
    assert estado == 200 and len(resultado["tokens"]) == 5 and resultado["html"].count("<svg") == 10
    if origen:
        assert headers["Access-Control-Allow-Origin"] == origen
        estado, _, headers = solicitar(base, "/api/analizar", origen=origen, metodo="OPTIONS")
        assert estado == 200 and "POST" in headers["Access-Control-Allow-Methods"]
    estado, _, _ = solicitar(base, "/static/no-existe.txt")
    assert estado == 404
    estado, _, _ = solicitar(base, datos=urlencode({"texto": " " * (1024 * 1024 + 1)}).encode(), tipo="application/x-www-form-urlencoded")
    assert estado == 413
    print("HTTP correcto: salud, GET, POST, API JSON, TXT multipart, 10 SVG, cache, 404 y 413" + (", CORS y OPTIONS" if origen else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:10000")
    parser.add_argument("--origen")
    argumentos = parser.parse_args()
    verificar(argumentos.url, argumentos.origen)
