from flask import Blueprint, request

from caronauvv.auth.decorators import login_required
from caronauvv.errors import ApiError
from caronauvv.limite import limitar

from .externos import buscar_ruas, consultar_cep
from .services import CIDADES, buscar_bairros, distancia_ate_uvv

bp = Blueprint("lugares", __name__)  # /api/lugares


@bp.get("/bairros")
@limitar(120, 60)   # publica (o cadastro usa): em media 2 por segundo por IP
def bairros():
    termo = (request.args.get("q") or "")[:60]
    limite = min(max(request.args.get("limite", default=10, type=int), 1), 20)
    return {"bairros": buscar_bairros(termo, limite)}


@bp.get("/cep/<cep>")
@login_required
@limitar(30, 60)
def cep(cep):
    digitos = "".join(c for c in cep if c.isdigit())
    if len(digitos) != 8:
        raise ApiError("CEP inválido: use 8 números (ex.: 29102-920).", campos={"cep": "Use 8 números."})
    endereco = consultar_cep(digitos)
    if endereco is None:
        raise ApiError("CEP não encontrado (ou o serviço de CEP está fora do ar). Preencha à mão.", 404)
    return {"endereco": endereco}


@bp.get("/ruas")
@login_required
@limitar(30, 60)
def ruas():
    cidade = request.args.get("cidade") or "Vila Velha"
    if cidade not in CIDADES:
        raise ApiError(f"cidade deve ser uma de: {', '.join(CIDADES)}.")
    resultado = buscar_ruas(request.args.get("q") or "", cidade)
    return {"ruas": resultado or [], "disponivel": resultado is not None}


@bp.get("/distancia")
@login_required
@limitar(30, 60)
def distancia():
    resultado = distancia_ate_uvv(request.args.get("bairro") or "")
    if resultado is None:
        raise ApiError("Bairro fora da lista: informe a distância à mão.", 404)
    return resultado


@bp.get("/onibus")
@login_required
@limitar(30, 60)
def onibus():
    """Sugestao de onibus (estimativa, sem horario oficial) entre o bairro e a UVV."""
    from .onibus import recomendar_onibus

    sentido = request.args.get("sentido", "ida")
    if sentido not in ("ida", "volta"):
        raise ApiError("sentido deve ser ida ou volta.")
    hora = request.args.get("hora", default=7, type=int)
    if not 0 <= hora <= 23:
        raise ApiError("hora deve ser de 0 a 23.")
    resultado = recomendar_onibus(request.args.get("bairro") or "", sentido, hora)
    if resultado is None:
        raise ApiError("Bairro fora da lista da Grande Vitória.", 404)
    return resultado
