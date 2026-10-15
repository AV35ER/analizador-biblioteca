import os

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
worker_class = "sync"
timeout = 30
graceful_timeout = 30
preload_app = True
accesslog = "-"
errorlog = "-"
capture_output = True


def on_starting(server):
    from automatas import generar_todos

    generar_todos()
    server.log.info("AFND, AFD y SVG preparados en memoria")
