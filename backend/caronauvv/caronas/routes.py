from flask import Blueprint, g, request

from caronauvv.auth.decorators import login_required

from .services import (
    aceitar_solicitacao,
    buscar_carona,
    buscar_solicitacao,
    cancelar_carona,
    cancelar_solicitacao,
    concluir_carona,
    caronas_do_motorista,
    criar_carona,
    editar_carona,
    listar_caronas,
    pedir_vaga,
    recusar_solicitacao,
    solicitacoes_da_carona,
    solicitacoes_do_passageiro,
)

bp = Blueprint("caronas", __name__)                    # /api/caronas
bp_solicitacoes = Blueprint("solicitacoes", __name__)  # /api/solicitacoes


def _json() -> dict:
    return request.get_json(silent=True) or {}


# ==========================================================
# BUSCA / CONSULTA
# ==========================================================
@bp.get("")
@login_required
def listar():
    caronas = listar_caronas(request.args)
    return {"caronas": [c.to_dict(g.usuario) for c in caronas]}


@bp.get("/minhas")
@login_required
def minhas():
    caronas = caronas_do_motorista(g.usuario, request.args.get("status"))
    return {"caronas": [c.to_dict(g.usuario) for c in caronas]}


@bp.get("/<int:carona_id>")
@login_required
def detalhe(carona_id):
    return {"carona": buscar_carona(carona_id).to_dict(g.usuario)}


# ==========================================================
# MOTORISTA: CRIAR / EDITAR / CANCELAR
# ==========================================================
@bp.post("")
@login_required
def criar():
    carona = criar_carona(g.usuario, _json())
    return {"carona": carona.to_dict(g.usuario)}, 201


@bp.put("/<int:carona_id>")
@login_required
def editar(carona_id):
    carona = editar_carona(buscar_carona(carona_id), g.usuario, _json())
    return {"carona": carona.to_dict(g.usuario)}


@bp.post("/<int:carona_id>/cancelar")
@login_required
def cancelar(carona_id):
    carona = cancelar_carona(buscar_carona(carona_id), g.usuario)
    return {"carona": carona.to_dict(g.usuario)}


@bp.post("/<int:carona_id>/concluir")
@login_required
def concluir(carona_id):
    carona = concluir_carona(buscar_carona(carona_id), g.usuario)
    return {"carona": carona.to_dict(g.usuario)}


# ==========================================================
# SOLICITACOES DE UMA CARONA
# ==========================================================
@bp.post("/<int:carona_id>/solicitacoes")
@login_required
def pedir(carona_id):
    solicitacao = pedir_vaga(buscar_carona(carona_id), g.usuario, _json())
    return {"solicitacao": solicitacao.to_dict(g.usuario)}, 201


@bp.get("/<int:carona_id>/solicitacoes")
@login_required
def pedidos_recebidos(carona_id):
    solicitacoes = solicitacoes_da_carona(buscar_carona(carona_id), g.usuario)
    return {"solicitacoes": [s.to_dict(g.usuario) for s in solicitacoes]}


# ==========================================================
# PASSAGEIRO: "MINHAS CARONAS" / MOTORISTA: ACEITAR E RECUSAR
# ==========================================================
@bp_solicitacoes.get("/minhas")
@login_required
def minhas_solicitacoes():
    solicitacoes = solicitacoes_do_passageiro(g.usuario, request.args.get("status"))
    return {"solicitacoes": [
        {**s.to_dict(g.usuario), "carona": s.carona.to_dict(g.usuario)} for s in solicitacoes
    ]}


@bp_solicitacoes.post("/<int:solicitacao_id>/aceitar")
@login_required
def aceitar(solicitacao_id):
    solicitacao = aceitar_solicitacao(buscar_solicitacao(solicitacao_id), g.usuario)
    return {"solicitacao": solicitacao.to_dict(g.usuario)}


@bp_solicitacoes.post("/<int:solicitacao_id>/recusar")
@login_required
def recusar(solicitacao_id):
    solicitacao = recusar_solicitacao(buscar_solicitacao(solicitacao_id), g.usuario)
    return {"solicitacao": solicitacao.to_dict(g.usuario)}


@bp_solicitacoes.post("/<int:solicitacao_id>/cancelar")
@login_required
def cancelar_pedido(solicitacao_id):
    solicitacao = cancelar_solicitacao(buscar_solicitacao(solicitacao_id), g.usuario)
    return {"solicitacao": solicitacao.to_dict(g.usuario)}
