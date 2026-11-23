from flask import Blueprint, g, request

from caronauvv.auth.decorators import login_required
from caronauvv.errors import ApiError
from caronauvv.validacao import validar

from .combustivel import calcular_rateio
from .schemas import CaronaEdicaoSchema, CaronaNovaSchema, PedidoVagaSchema, PinSchema, PosicaoSchema
from .services import (
    aceitar_solicitacao,
    buscar_carona,
    buscar_solicitacao,
    cancelar_carona,
    cancelar_solicitacao,
    caronas_do_motorista,
    concluir_carona,
    confirmar_embarque,
    criar_carona,
    editar_carona,
    iniciar_carona,
    listar_caronas,
    marcar_falta,
    pedir_vaga,
    recusar_solicitacao,
    registrar_posicao,
    solicitacoes_da_carona,
    solicitacoes_do_passageiro,
    teto_rateio,
    valor_sugerido,
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
    caronas = listar_caronas(request.args, g.usuario)
    return {"caronas": [c.to_dict(g.usuario) for c in caronas]}


@bp.get("/minhas")
@login_required
def minhas():
    caronas = caronas_do_motorista(g.usuario, request.args.get("status"))
    return {"caronas": [c.to_dict(g.usuario) for c in caronas]}


@bp.get("/valor-sugerido")
@login_required
def sugerir_valor():
    distancia = request.args.get("distancia_km", type=float)
    vagas = request.args.get("vagas", default=3, type=int)
    if distancia is None or distancia < 0 or not 1 <= vagas <= 6:
        raise ApiError("Informe distancia_km (>= 0) e vagas (1 a 6).")
    teto = teto_rateio()
    energia = request.args.get("energia")
    if energia:
        # Conta completa: litros (ou kWh), preco, custo da viagem, parte de cada um e adicional
        rateio = calcular_rateio(distancia, vagas, energia, request.args.get("consumo_km"),
                                 request.args.get("adicional", 0))
        return {
            "valor_sugerido": float(rateio.valor_por_passageiro), "teto": float(teto),
            "acima_do_teto": rateio.valor_por_passageiro > teto, "calculo": rateio.to_dict(),
        }
    return {"valor_sugerido": float(valor_sugerido(distancia, vagas)), "teto": float(teto)}


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
    carona = criar_carona(g.usuario, validar(CaronaNovaSchema, _json()))
    return {"carona": carona.to_dict(g.usuario)}, 201


@bp.put("/<int:carona_id>")
@login_required
def editar(carona_id):
    carona = buscar_carona(carona_id)
    carona = editar_carona(carona, g.usuario, validar(CaronaEdicaoSchema, _json()))
    return {"carona": carona.to_dict(g.usuario)}


@bp.post("/<int:carona_id>/cancelar")
@login_required
def cancelar(carona_id):
    carona = cancelar_carona(buscar_carona(carona_id), g.usuario)
    return {"carona": carona.to_dict(g.usuario)}


# ==========================================================
# MOTORISTA: CICLO DA VIAGEM
# ==========================================================
@bp.post("/<int:carona_id>/iniciar")
@login_required
def iniciar(carona_id):
    carona = iniciar_carona(buscar_carona(carona_id), g.usuario)
    return {"carona": carona.to_dict(g.usuario)}


@bp.post("/<int:carona_id>/concluir")
@login_required
def concluir(carona_id):
    carona = concluir_carona(buscar_carona(carona_id), g.usuario)
    return {"carona": carona.to_dict(g.usuario)}


@bp.post("/<int:carona_id>/posicao")
@login_required
def posicao(carona_id):
    dados = validar(PosicaoSchema, _json())
    registrar_posicao(buscar_carona(carona_id), g.usuario, dados.lat, dados.lng)
    return {"message": "Posição registrada."}, 201


# ==========================================================
# SOLICITACOES DE UMA CARONA
# ==========================================================
@bp.post("/<int:carona_id>/solicitacoes")
@login_required
def pedir(carona_id):
    carona = buscar_carona(carona_id)
    solicitacao = pedir_vaga(carona, g.usuario, validar(PedidoVagaSchema, _json()))
    return {"solicitacao": solicitacao.to_dict(g.usuario)}, 201


@bp.get("/<int:carona_id>/solicitacoes")
@login_required
def pedidos_recebidos(carona_id):
    solicitacoes = solicitacoes_da_carona(buscar_carona(carona_id), g.usuario)
    return {"solicitacoes": [s.to_dict(g.usuario) for s in solicitacoes]}


# ==========================================================
# PASSAGEIRO: "MEUS PEDIDOS" / MOTORISTA: ACEITAR, RECUSAR, EMBARQUE
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


@bp_solicitacoes.post("/<int:solicitacao_id>/embarque")
@login_required
def embarque(solicitacao_id):
    pin = validar(PinSchema, _json()).pin
    solicitacao = confirmar_embarque(buscar_solicitacao(solicitacao_id), g.usuario, pin)
    return {"solicitacao": solicitacao.to_dict(g.usuario)}


@bp_solicitacoes.post("/<int:solicitacao_id>/falta")
@login_required
def falta(solicitacao_id):
    solicitacao = marcar_falta(buscar_solicitacao(solicitacao_id), g.usuario)
    return {"solicitacao": solicitacao.to_dict(g.usuario)}
