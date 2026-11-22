from flask import Blueprint, g, request

from .decorators import login_required
from .services import (
    atualizar_perfil,
    autenticar,
    buscar_veiculo,
    cadastrar_usuario,
    cadastrar_veiculo,
    editar_veiculo,
    gerar_token,
    remover_veiculo,
)

bp = Blueprint("auth", __name__)                # /api/auth
bp_veiculos = Blueprint("veiculos", __name__)   # /api/veiculos


def _json() -> dict:
    return request.get_json(silent=True) or {}


# ==========================================================
# CADASTRO / LOGIN / LOGOUT
# ==========================================================
@bp.post("/cadastro")
def cadastro():
    usuario = cadastrar_usuario(_json())
    return {"usuario": usuario.to_dict(privado=True), "token": gerar_token(usuario)}, 201


@bp.post("/login")
def login():
    dados = _json()
    usuario = autenticar(dados.get("login"), dados.get("senha"))
    return {"usuario": usuario.to_dict(privado=True), "token": gerar_token(usuario)}


@bp.post("/logout")
@login_required
def logout():
    # Token sem estado: basta o frontend apagar o token salvo.
    return {"message": "Logout realizado."}


# ==========================================================
# PERFIL DO USUARIO LOGADO
# ==========================================================
@bp.get("/me")
@login_required
def perfil():
    return {"usuario": g.usuario.to_dict(privado=True)}


@bp.put("/me")
@login_required
def editar_perfil():
    usuario = atualizar_perfil(g.usuario, _json())
    return {"usuario": usuario.to_dict(privado=True)}


# ==========================================================
# VEICULOS DO USUARIO LOGADO (/api/veiculos)
# ==========================================================
@bp_veiculos.get("")
@login_required
def listar_veiculos():
    return {"veiculos": [v.to_dict(com_placa=True) for v in g.usuario.veiculos]}


@bp_veiculos.post("")
@login_required
def novo_veiculo():
    veiculo = cadastrar_veiculo(g.usuario, _json())
    return {"veiculo": veiculo.to_dict(com_placa=True)}, 201


@bp_veiculos.put("/<int:veiculo_id>")
@login_required
def alterar_veiculo(veiculo_id):
    veiculo = editar_veiculo(buscar_veiculo(veiculo_id, g.usuario), _json())
    return {"veiculo": veiculo.to_dict(com_placa=True)}


@bp_veiculos.delete("/<int:veiculo_id>")
@login_required
def apagar_veiculo(veiculo_id):
    remover_veiculo(buscar_veiculo(veiculo_id, g.usuario))
    return {"message": "Veículo removido."}
