import logging
import time

from flask import Flask, g, request


# ==========================================================
# LOGGING
# Formato: data | nivel | modulo | mensagem
# Cada requisicao da API gera uma linha (metodo, rota, status e tempo),
# e erros inesperados saem com o traceback completo (ver errors.py).
# ==========================================================
FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def init_app(app: Flask) -> None:
    nivel = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(FORMATO, datefmt="%Y-%m-%d %H:%M:%S"))

    logger = logging.getLogger("caronauvv")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(nivel)
    logger.propagate = False

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(nivel)

    @app.before_request
    def _inicio():
        g._inicio_req = time.perf_counter()

    @app.after_request
    def _registrar(resposta):
        if request.path.startswith("/api"):
            ms = (time.perf_counter() - g.get("_inicio_req", time.perf_counter())) * 1000
            logger.info("%s %s -> %s (%.0f ms)", request.method, request.path, resposta.status_code, ms)
        return resposta
