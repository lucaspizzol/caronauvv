from flask import Blueprint, g, request

from caronauvv.auth.decorators import login_required
from caronauvv.caronas.services import buscar_carona
from caronauvv.validacao import validar

from .schemas import MOTIVOS_DENUNCIA, DenunciaSchema, SosSchema
from .services import acionar_sos, acompanhar, compartilhar_viagem, denunciar

bp = Blueprint("seguranca", __name__)  # /api


def _json() -> dict:
    return request.get_json(silent=True) or {}


@bp.post("/caronas/<int:carona_id>/compartilhar")
@login_required
def compartilhar(carona_id):
    link = compartilhar_viagem(buscar_carona(carona_id), g.usuario)
    return {"link": {**link.to_dict(), "caminho": f"/acompanhar/{link.token}"}}, 201


@bp.get("/acompanhar/<token>")
def ver_viagem(token):
    # Rota PUBLICA (sem login): e o link que a familia recebe
    return {"viagem": acompanhar(token)}


@bp.post("/caronas/<int:carona_id>/sos")
@login_required
def sos(carona_id):
    alerta = acionar_sos(buscar_carona(carona_id), g.usuario, validar(SosSchema, _json()))
    contatos = [c.to_dict() for c in g.usuario.contatos_confianca]
    return {"alerta": alerta.to_dict(), "contatos": contatos, "emergencia": "190"}, 201


@bp.get("/denuncias/motivos")
@login_required
def motivos():
    return {"motivos": list(MOTIVOS_DENUNCIA)}


@bp.post("/denuncias")
@login_required
def nova_denuncia():
    denuncia = denunciar(g.usuario, validar(DenunciaSchema, _json()))
    return {"denuncia": {"id": denuncia.id, "status": denuncia.status}}, 201
