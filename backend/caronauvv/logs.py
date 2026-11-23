import logging
import os
import time
from logging.handlers import RotatingFileHandler

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

    handlers = [handler]
    # Opcional: tambem grava em arquivo (LOG_FILE no .env), com rotacao de 1 MB x 5 arquivos
    caminho = app.config.get("LOG_FILE")
    if caminho:
        os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
        arquivo = RotatingFileHandler(caminho, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        arquivo.setFormatter(handler.formatter)
        handlers.append(arquivo)

    logger = logging.getLogger("caronauvv")
    logger.handlers.clear()
    for h in handlers:
        logger.addHandler(h)
    logger.setLevel(nivel)
    logger.propagate = False

    app.logger.handlers.clear()
    for h in handlers:
        app.logger.addHandler(h)
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
