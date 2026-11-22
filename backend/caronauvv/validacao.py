"""
VALIDACAO DOS FORMULARIOS NO SERVIDOR (Pydantic)

Cada modulo define seus "schemas" (auth/schemas.py, caronas/schemas.py, ...):
classes Pydantic que descrevem os campos de um formulario, os tipos e as regras.
As rotas chamam `validar(Schema, request.get_json())` antes de chegar no service.

Se algum campo estiver errado, `validar` levanta ApiError(400) e a API responde:
    {
      "error": "Campos obrigatórios: nome, telefone.",      # mensagem geral
      "campos": {"nome": "Campo obrigatório.", ...}          # erro de cada campo
    }
O frontend usa "campos" para pintar de vermelho o campo certo do formulario.
"""
import re
from typing import Annotated, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError

from caronauvv.errors import ApiError

S = TypeVar("S", bound=BaseModel)


# ==========================================================
# SCHEMA BASE
# - str_strip_whitespace: tira espacos das pontas de todo texto
# - extra="ignore": campos desconhecidos sao ignorados (nao quebram a API)
# ==========================================================
class Schema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    def preenchidos(self) -> dict:
        """So os campos que vieram no JSON (usado nas edicoes parciais / PUT)."""
        return self.model_dump(exclude_unset=True)


# ==========================================================
# TIPOS REUTILIZAVEIS
# ==========================================================
def _vazio_vira_none(valor):
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def _somente_digitos(valor):
    if valor is None:
        return valor
    return re.sub(r"\D", "", str(valor))


# Texto opcional: "" ou "   " viram None (o banco guarda NULL, nao string vazia)
TextoOpcional = Annotated[str | None, BeforeValidator(_vazio_vira_none)]

# Telefone: aceita "(27) 99999-0000" e guarda so os numeros
Digitos = Annotated[str, BeforeValidator(_somente_digitos)]


# ==========================================================
# TRADUCAO DOS ERROS DO PYDANTIC PARA PORTUGUES
# ==========================================================
MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Campo obrigatório.",
    "string_type": "Informe um texto.",
    "int_parsing": "Precisa ser um número inteiro.",
    "int_type": "Precisa ser um número inteiro.",
    "int_from_float": "Precisa ser um número inteiro.",
    "float_parsing": "Precisa ser um número.",
    "float_type": "Precisa ser um número.",
    "decimal_parsing": "Precisa ser um número.",
    "decimal_type": "Precisa ser um número.",
    "finite_number": "Precisa ser um número.",
    "bool_parsing": "Precisa ser verdadeiro ou falso.",
    "bool_type": "Precisa ser verdadeiro ou falso.",
    "datetime_parsing": "Data/hora inválida (use AAAA-MM-DDTHH:MM).",
    "datetime_from_date_parsing": "Data/hora inválida (use AAAA-MM-DDTHH:MM).",
    "datetime_type": "Data/hora inválida (use AAAA-MM-DDTHH:MM).",
    "literal_error": "Valor não permitido.",
    "enum": "Valor não permitido.",
    "list_type": "Precisa ser uma lista.",
    "too_long": "Itens demais.",
}


def _mensagem(erro: dict) -> str:
    tipo = erro["type"]
    ctx = erro.get("ctx") or {}
    if tipo == "value_error":
        # ValueError("...") levantado dentro de um @field_validator
        return str(ctx.get("error", erro["msg"])).removeprefix("Value error, ")
    if tipo == "string_too_long":
        return f"Máximo de {ctx.get('max_length')} caracteres."
    if tipo in ("greater_than_equal", "greater_than"):
        return f"O valor mínimo é {ctx.get('ge', ctx.get('gt'))}."
    if tipo in ("less_than_equal", "less_than"):
        return f"O valor máximo é {ctx.get('le', ctx.get('lt'))}."
    if tipo == "literal_error":
        return f"Use um destes valores: {ctx.get('expected', '')}."
    return MENSAGENS.get(tipo, erro["msg"])


def validar(schema: type[S], dados) -> S:
    """Valida o JSON recebido com o schema; em caso de erro levanta ApiError(400)."""
    if not isinstance(dados, dict):
        raise ApiError("Envie os dados em JSON.")
    try:
        return schema.model_validate(dados)
    except ValidationError as exc:
        campos: dict[str, str] = {}
        faltando: list[str] = []
        for erro in exc.errors():
            campo = ".".join(str(p) for p in erro["loc"]) or "geral"
            if campo in campos:
                continue
            campos[campo] = _mensagem(erro)
            if erro["type"] in ("missing", "string_too_short"):
                faltando.append(campo)

        if faltando:
            mensagem = f"Campos obrigatórios: {', '.join(faltando)}."
        else:
            campo, texto = next(iter(campos.items()))
            mensagem = texto if campo == "geral" else f"{campo}: {texto}"
        raise ApiError(mensagem, 400, campos=campos) from None
