from flask import Blueprint, g, request

from caronauvv.auth.decorators import login_required
from caronauvv.caronas.services import buscar_solicitacao
from caronauvv.validacao import validar

from .models import TAGS_MOTORISTA, TAGS_PASSAGEIRO
from .schemas import AvaliacaoSchema
from .services import avaliacoes_pendentes, avaliar, informar_pagamento, obter_pix

bp = Blueprint("avaliacoes", __name__)  # /api


@bp.get("/avaliacoes/pendentes")
@login_required
def pendentes():
    return {"pendentes": avaliacoes_pendentes(g.usuario)}


@bp.get("/avaliacoes/tags")
@login_required
def tags():
    return {"motorista": list(TAGS_MOTORISTA), "passageiro": list(TAGS_PASSAGEIRO)}


@bp.post("/solicitacoes/<int:solicitacao_id>/avaliacao")
@login_required
def nova_avaliacao(solicitacao_id):
    dados = validar(AvaliacaoSchema, request.get_json(silent=True) or {})
    avaliacao = avaliar(buscar_solicitacao(solicitacao_id), g.usuario, dados)
    return {"avaliacao": {"id": avaliacao.id, "nota": avaliacao.nota}}, 201


@bp.get("/solicitacoes/<int:solicitacao_id>/pix")
@login_required
def pix(solicitacao_id):
    return {"pagamento": obter_pix(buscar_solicitacao(solicitacao_id), g.usuario).to_dict()}


@bp.post("/solicitacoes/<int:solicitacao_id>/pagamento")
@login_required
def pagar(solicitacao_id):
    metodo = (request.get_json(silent=True) or {}).get("metodo", "pix")
    pagamento = informar_pagamento(buscar_solicitacao(solicitacao_id), g.usuario, metodo)
    return {"pagamento": pagamento.to_dict()}
