import logging

from flask import Flask
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("caronauvv")


class ApiError(Exception):
    """
    Erro de regra de negocio levantado pelos services.
    O handler registrado em init_app() transforma em JSON:
        {"error": "<mensagem>"}, status_code
    """

    def __init__(self, mensagem: str, status_code: int = 400, campos: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_code = status_code
        self.campos = campos  # erro de cada campo do formulario (validacao.py)


# ==========================================================
# TRATAMENTO CENTRAL DE ERROS
# Toda resposta de erro da API sai no mesmo formato: {"error": "..."}
# ==========================================================
MENSAGENS_HTTP = {
    400: "Requisição inválida.",
    401: "Faça login para continuar.",
    403: "Acesso negado.",
    404: "Recurso não encontrado.",
    405: "Método não permitido para esta rota.",
    413: "Arquivo grande demais.",
}


def init_app(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _erro_de_negocio(erro: ApiError):
        nivel = logging.WARNING if erro.status_code >= 500 else logging.INFO
        logger.log(nivel, "Regra de negocio (%s): %s", erro.status_code, erro.mensagem)
        corpo = {"error": erro.mensagem}
        if erro.campos:
            corpo["campos"] = erro.campos
        return corpo, erro.status_code

    @app.errorhandler(HTTPException)
    def _erro_http(erro: HTTPException):
        return {"error": MENSAGENS_HTTP.get(erro.code, erro.description)}, erro.code

    @app.errorhandler(Exception)
    def _erro_inesperado(erro: Exception):
        # Nunca devolve o stack trace para o cliente; ele vai so para o log.
        logger.exception("Erro inesperado: %s", erro)
        return {"error": "Erro interno no servidor. Tente novamente em instantes."}, 500
