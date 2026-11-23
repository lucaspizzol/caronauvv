from flask import Blueprint, g, request

from caronauvv.auth.decorators import admin_required

from .services import (
    analisar_denuncia,
    atualizar_configuracoes,
    estrutura_do_banco,
    listar_alertas,
    listar_configuracoes,
    listar_denuncias,
    listar_usuarios,
    remover_foto_usuario,
    resetar_dois_fatores,
    resolver_alerta,
    resumo,
    suspender_usuario,
    verificar_usuario,
)

bp = Blueprint("admin", __name__)  # /api/admin  (todas as rotas exigem is_admin)


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _usuario_admin(u) -> dict:
    return {
        **u.to_dict(privado=True),
        "is_active": u.is_active,
        "ultimo_login_em": u.ultimo_login_em.isoformat(timespec="minutes") if u.ultimo_login_em else None,
    }


@bp.get("/resumo")
@admin_required
def indicadores():
    return {"resumo": resumo()}


# ---------------- usuarios ----------------
@bp.get("/usuarios")
@admin_required
def usuarios():
    lista = listar_usuarios(request.args.get("busca", ""), request.args.get("pendentes") == "1")
    return {"usuarios": [_usuario_admin(u) for u in lista]}


@bp.post("/usuarios/<int:usuario_id>/verificar")
@admin_required
def verificar(usuario_id):
    aprovado = bool(_json().get("aprovado", True))
    return {"usuario": _usuario_admin(verificar_usuario(usuario_id, aprovado))}


@bp.post("/usuarios/<int:usuario_id>/suspender")
@admin_required
def suspender(usuario_id):
    ativo = bool(_json().get("ativo", False))
    return {"usuario": _usuario_admin(suspender_usuario(usuario_id, g.usuario, ativo))}


@bp.delete("/usuarios/<int:usuario_id>/foto")
@admin_required
def remover_foto(usuario_id):
    return {"usuario": _usuario_admin(remover_foto_usuario(usuario_id))}


@bp.post("/usuarios/<int:usuario_id>/resetar-2fa")
@admin_required
def resetar_2fa(usuario_id):
    return {"usuario": _usuario_admin(resetar_dois_fatores(usuario_id))}


# ---------------- denuncias ----------------
@bp.get("/denuncias")
@admin_required
def denuncias():
    return {"denuncias": [d.to_dict() for d in listar_denuncias(request.args.get("status"))]}


@bp.post("/denuncias/<int:denuncia_id>")
@admin_required
def analisar(denuncia_id):
    dados = _json()
    denuncia = analisar_denuncia(
        denuncia_id, g.usuario, str(dados.get("status", "")),
        (str(dados.get("resolucao") or "").strip() or None), bool(dados.get("suspender", False)),
    )
    return {"denuncia": denuncia.to_dict()}


# ---------------- alertas ----------------
@bp.get("/alertas")
@admin_required
def alertas():
    return {"alertas": [a.to_dict() for a in listar_alertas()]}


@bp.post("/alertas/<int:alerta_id>/resolver")
@admin_required
def resolver(alerta_id):
    return {"alerta": resolver_alerta(alerta_id).to_dict()}


# ---------------- configuracoes ----------------
def _configs(lista) -> list[dict]:
    return [{"chave": c.chave, "valor": c.valor, "descricao": c.descricao} for c in lista]


@bp.get("/configuracoes")
@admin_required
def configuracoes():
    return {"configuracoes": _configs(listar_configuracoes())}


@bp.put("/configuracoes")
@admin_required
def salvar_configuracoes():
    return {"configuracoes": _configs(atualizar_configuracoes(_json()))}


# ---------------- banco de dados ----------------
@bp.get("/banco")
@admin_required
def banco():
    return estrutura_do_banco()
