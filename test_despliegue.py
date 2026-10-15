import io
import os
import runpy
import subprocess
import sys
import tomllib
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import Mock, patch

from app import LIMITE_ENTRADA, app


class DespliegueTests(unittest.TestCase):
    def setUp(self):
        self.cliente = app.test_client()

    def test_salud_y_cache(self):
        respuesta = self.cliente.get("/healthz")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json, {"status": "ok"})
        self.assertEqual(respuesta.headers["Cache-Control"], "no-store")
        self.assertEqual(self.cliente.get("/").headers["Cache-Control"], "no-store")
        self.assertFalse(app.debug)

    def test_limite_real_archivo_y_texto(self):
        for longitud, esperado in ((LIMITE_ENTRADA, 200), (LIMITE_ENTRADA + 1, 413)):
            respuesta = self.cliente.post("/", data={"texto": "ignorado", "archivo": (io.BytesIO(b" " * longitud), "limite.txt")})
            self.assertEqual(respuesta.status_code, esperado)
            self.assertEqual(respuesta.headers["Cache-Control"], "no-store")
            respuesta.request.close()
            respuesta.request.environ["wsgi.input"].close()
            respuesta = self.cliente.post("/", data={"texto": " " * longitud}, content_type="multipart/form-data")
            self.assertEqual(respuesta.status_code, esperado)
            respuesta.request.environ["wsgi.input"].close()

    def test_limite_total_solicitud(self):
        respuesta = self.cliente.post("/", data=b"x" * (app.config["MAX_CONTENT_LENGTH"] + 1), content_type="application/x-www-form-urlencoded")
        self.assertEqual(respuesta.status_code, 413)

    def test_configuracion_netlify(self):
        with open("netlify.toml", "rb") as archivo:
            config = tomllib.load(archivo)
        self.assertTrue(Path(config["build"]["publish"]).is_dir())
        self.assertTrue(any(Path(config["build"]["publish"]).iterdir()))
        self.assertEqual(config["build"]["command"], "python generar_frontend.py")
        self.assertNotIn("redirects", config)
        self.assertIn("plan: free", Path("render.yaml").read_text())

    def test_api_cors_y_equivalencia_interfaz(self):
        origen = "https://biblioteca-prueba.netlify.app"
        with patch.dict(os.environ, {"CORS_ORIGINS": origen}):
            respuesta = self.cliente.options("/api/analizar", headers={"Origin": origen, "Access-Control-Request-Method": "POST"})
            self.assertEqual(respuesta.headers["Access-Control-Allow-Origin"], origen)
            self.assertIn("POST", respuesta.headers["Access-Control-Allow-Methods"])
            self.assertNotIn("Access-Control-Allow-Origin", self.cliente.get("/healthz", headers={"Origin": "https://otro.invalid"}).headers)
            respuesta = self.cliente.post("/api/analizar", data={"archivo": (io.BytesIO(b"RESERVAR L025\nU104 7;"), "entrada.txt")}, headers={"Origin": origen})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.headers["Access-Control-Allow-Origin"], origen)
            self.assertEqual(len(respuesta.json["tokens"]), 5)
            self.assertEqual(respuesta.json["errores"], [])
            self.assertEqual(respuesta.json["html"].count("<svg"), 10)
            pagina = self.cliente.post("/", data={"texto": "RESERVAR L025\nU104 7;"}).get_data(as_text=True)
            self.assertIn(respuesta.json["html"], pagina)
            grande = self.cliente.post("/api/analizar", data={"texto": "x" * (LIMITE_ENTRADA + 1)}, headers={"Origin": origen})
            self.assertEqual(grande.status_code, 413)
            self.assertEqual(grande.headers["Access-Control-Allow-Origin"], origen)
            self.assertIn("mensaje", grande.json)
        invalida = self.cliente.post("/api/analizar", data={"texto": "RESERVAR X025 U104 7;"})
        self.assertEqual(len(invalida.json["tokens"]), 4)
        self.assertEqual(invalida.json["errores"][0]["lexema"], "X025")
        self.assertEqual(self.cliente.post("/api/analizar", data={"texto": ""}).status_code, 400)

    def test_frontend_estatico_sin_graphviz(self):
        from generar_frontend import generar

        with patch("automatas.Digraph.pipe", side_effect=AssertionError("El frontend no debe necesitar dot")):
            generar()
        pagina = Path("netlify-public/index.html").read_text(encoding="utf-8")
        self.assertNotIn("{%", pagina)
        self.assertIn('src="/cliente.js"', pagina)
        self.assertIn('id="resultados"', pagina)
        self.assertIn("inicializarResultados", pagina)

    def test_configuracion_build_api(self):
        from generar_frontend import generar

        with TemporaryDirectory() as carpeta:
            with patch.dict(os.environ, {"NETLIFY": "true", "RENDER_API_URL": ""}):
                with self.assertRaises(ValueError):
                    generar(Path(carpeta))
            with patch.dict(os.environ, {"RENDER_API_URL": "https://api.example.org"}):
                generar(Path(carpeta))
            self.assertIn("https://api.example.org", Path(carpeta, "config.js").read_text())

    def test_puerto_y_precalentamiento(self):
        with patch.dict(os.environ, {"PORT": "12345"}):
            config = runpy.run_path("gunicorn.conf.py")
        self.assertEqual(config["bind"], "0.0.0.0:12345")
        self.assertTrue(config["preload_app"])
        with patch("automatas.generar_todos") as generar:
            config["on_starting"](Mock())
        generar.assert_called_once_with()

    @unittest.skipIf(sys.platform == "win32", "Gunicorn requiere Unix; ejecutar en Docker/Linux")
    def test_gunicorn_importa_aplicacion(self):
        resultado = subprocess.run(
            [sys.executable, "-m", "gunicorn", "--config", "gunicorn.conf.py", "--check-config", "app:app"],
            capture_output=True, text=True, timeout=30
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == "__main__":
    unittest.main()
