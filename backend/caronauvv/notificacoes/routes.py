from flask import Blueprint, g

from caronauvv.auth.decorators import login_required

from caronauvv.caronas.services import expirar_pedidos_do_usuario

from .services import contar_nao_lidas, listar, marcar_todas_como_lidas

bp = Blueprint("notificacoes", __name__)  # /api/notificacoes


@bp.get("")
@login_required
def minhas():
    expirar_pedidos_do_usuario(g.usuario)
    notificacoes, nao_lidas = listar(g.usuario)
    return {"notificacoes": [n.to_dict() for n in notificacoes], "nao_lidas": nao_lidas}


@bp.get("/contagem")
@login_required
def contagem():
    # Chamada a cada poucos segundos pelo sino do menu: so o numero, bem leve
    # (antes expira os pedidos vencidos, para o aviso de "pedido expirou" chegar na hora)
    expirar_pedidos_do_usuario(g.usuario)
    return {"nao_lidas": contar_nao_lidas(g.usuario)}


@bp.post("/lidas")
@login_required
def ler_todas():
    return {"marcadas": marcar_todas_como_lidas(g.usuario)}
