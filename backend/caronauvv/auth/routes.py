from flask import Blueprint, current_app, g, request

from caronauvv.validacao import validar

from .decorators import login_required
from .schemas import (
    CadastroSchema,
    CodigoSchema,
    ContatoSchema,
    LoginSchema,
    PerfilSchema,
    VeiculoEdicaoSchema,
    VeiculoSchema,
)
from .services import (
    adicionar_contato,
    atualizar_perfil,
    autenticar,
    buscar_usuario,
    buscar_veiculo,
    cadastrar_usuario,
    cadastrar_veiculo,
    editar_veiculo,
    gerar_token,
    perfil_publico,
    reenviar_codigo,
    remover_contato,
    remover_veiculo,
    solicitar_verificacao_perfil,
    verificar_email,
)

bp = Blueprint("auth", __name__)                # /api/auth
bp_veiculos = Blueprint("veiculos", __name__)   # /api/veiculos
bp_usuarios = Blueprint("usuarios", __name__)   # /api/usuarios
bp_contatos = Blueprint("contatos", __name__)   # /api/contatos


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _com_codigo_dev(corpo: dict, codigo: str) -> dict:
    # Sem servidor de e-mail (desenvolvimento), o codigo volta na resposta para a demonstracao
    if current_app.config.get("MOSTRAR_CODIGO_DEV"):
        corpo["codigo_dev"] = codigo
    return corpo


# ==========================================================
# CADASTRO / LOGIN / LOGOUT
# ==========================================================
@bp.post("/cadastro")
def cadastro():
    usuario, codigo = cadastrar_usuario(validar(CadastroSchema, _json()))
    corpo = {"usuario": usuario.to_dict(privado=True), "token": gerar_token(usuario)}
    return _com_codigo_dev(corpo, codigo), 201


@bp.post("/login")
def login():
    dados = validar(LoginSchema, _json())
    usuario = autenticar(dados.login, dados.senha)
    return {"usuario": usuario.to_dict(privado=True), "token": gerar_token(usuario)}


@bp.post("/logout")
@login_required
def logout():
    # Token sem estado: basta o frontend apagar o token salvo.
    return {"message": "Logout realizado."}


# ==========================================================
# VERIFICACAO DE E-MAIL E DE PERFIL
# ==========================================================
@bp.post("/verificar-email")
@login_required
def confirmar_email():
    usuario = verificar_email(g.usuario, validar(CodigoSchema, _json()).codigo)
    return {"usuario": usuario.to_dict(privado=True)}


@bp.post("/reenviar-codigo")
@login_required
def novo_codigo():
    codigo = reenviar_codigo(g.usuario)
    return _com_codigo_dev({"message": f"Enviamos um novo código para {g.usuario.email}."}, codigo)


@bp.post("/solicitar-verificacao")
@login_required
def pedir_selo():
    usuario = solicitar_verificacao_perfil(g.usuario)
    return {"usuario": usuario.to_dict(privado=True)}


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
    usuario = atualizar_perfil(g.usuario, validar(PerfilSchema, _json()))
    return {"usuario": usuario.to_dict(privado=True)}


# ==========================================================
# PERFIL PUBLICO (/api/usuarios/<id>): reputacao, avaliacoes, carros
# ==========================================================
@bp_usuarios.get("/<int:usuario_id>")
@login_required
def ver_usuario(usuario_id):
    return {"usuario": perfil_publico(buscar_usuario(usuario_id))}


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
    veiculo = cadastrar_veiculo(g.usuario, validar(VeiculoSchema, _json()))
    return {"veiculo": veiculo.to_dict(com_placa=True)}, 201


@bp_veiculos.put("/<int:veiculo_id>")
@login_required
def alterar_veiculo(veiculo_id):
    veiculo = buscar_veiculo(veiculo_id, g.usuario)
    veiculo = editar_veiculo(veiculo, validar(VeiculoEdicaoSchema, _json()))
    return {"veiculo": veiculo.to_dict(com_placa=True)}


@bp_veiculos.delete("/<int:veiculo_id>")
@login_required
def apagar_veiculo(veiculo_id):
    remover_veiculo(buscar_veiculo(veiculo_id, g.usuario))
    return {"message": "Veículo removido."}


# ==========================================================
# CONTATOS DE CONFIANCA (/api/contatos)
# ==========================================================
@bp_contatos.get("")
@login_required
def listar_contatos():
    return {"contatos": [c.to_dict() for c in g.usuario.contatos_confianca]}


@bp_contatos.post("")
@login_required
def novo_contato():
    contato = adicionar_contato(g.usuario, validar(ContatoSchema, _json()))
    return {"contato": contato.to_dict()}, 201


@bp_contatos.delete("/<int:contato_id>")
@login_required
def apagar_contato(contato_id):
    remover_contato(g.usuario, contato_id)
    return {"message": "Contato removido."}
