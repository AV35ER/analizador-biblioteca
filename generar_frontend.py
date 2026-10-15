import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import render_template
from app import app, EJEMPLO, EXPRESIONES


def generar(destino=Path("netlify-public")):
    destino.mkdir(exist_ok=True)
    with app.test_request_context("/"):
        pagina = render_template(
            "index.html", texto=EJEMPLO, tokens=[], errores=[], mensaje="",
            analizado=False, resultados={}, expresiones=EXPRESIONES, modo_estatico=True
        )
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    origen = os.environ.get("RENDER_API_URL", "").strip().rstrip("/")
    if os.environ.get("NETLIFY") == "true" and not origen:
        raise ValueError("Configura RENDER_API_URL en Netlify con el origen HTTPS real de Render")
    if origen:
        partes = urlsplit(origen)
        if partes.scheme != "https" or not partes.hostname or partes.path or partes.query or partes.fragment or partes.username or partes.hostname.endswith(".invalid"):
            raise ValueError("RENDER_API_URL debe ser el origen HTTPS de Render, sin rutas")
        (destino / "config.js").write_text("window.BIBLIOTECA_API = " + json.dumps(origen) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    generar()
