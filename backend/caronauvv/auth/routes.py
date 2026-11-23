from flask import Blueprint, Response, current_app, g, request

from caronauvv.validacao import validar

from . import dois_fatores
from .decorators import login_required
from .foto import buscar_foto, remover_foto, salvar_foto
from .schemas import (
    CadastroSchema,
    CodigoSchema,
    ContatoSchema,
    EsqueciSenhaSchema,
    LoginSchema,
    PerfilSchema,
    RedefinirSenhaSchema,
    SegundaEtapaSchema,
    SenhaECodigoSchema,
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
    pedir_recuperacao,
    perfil_publico,
    redefinir_senha,
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
bp_fotos = Blueprint("fotos", __name__)         # /api/fotos


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


def _sessao(usuario) -> dict:
    return {"usuario": usuario.to_dict(privado=True), "token": gerar_token(usuario)}


@bp.post("/login")
def login():
    dados = validar(LoginSchema, _json())
    usuario = autenticar(dados.login, dados.senha)
    if usuario.totp_ativo:
        # Senha certa, mas a conta tem verificacao em duas etapas: ainda nao entrega o token.
        # O "desafio" prova, na segunda chamada, que a senha ja foi conferida.
        return {"precisa_2fa": True, "desafio": dois_fatores.gerar_desafio(usuario)}
    return _sessao(usuario)


@bp.post("/login/2fa")
def login_segunda_etapa():
    dados = validar(SegundaEtapaSchema, _json())
    usuario = dois_fatores.usuario_do_desafio(dados.desafio)
    metodo = dois_fatores.conferir_segundo_fator(usuario, dados.codigo)
    corpo = _sessao(usuario)
    if metodo == "reserva":
        restam = dois_fatores.codigos_restantes(usuario)
        corpo["aviso"] = f"Você entrou com um código de reserva. Restam {restam}."
    return corpo


@bp.post("/logout")
@login_required
def logout():
    # Token sem estado: basta o frontend apagar o token salvo.
    return {"message": "Logout realizado."}


# ==========================================================
# ESQUECI MINHA SENHA (codigo por e-mail)
# ==========================================================
@bp.post("/esqueci-senha")
def esqueci_senha():
    codigo = pedir_recuperacao(validar(EsqueciSenhaSchema, _json()).login)
    corpo = {"message": "Se a conta existir, enviamos um código de 6 números para o e-mail cadastrado."}
    return _com_codigo_dev(corpo, codigo) if codigo else corpo


@bp.post("/redefinir-senha")
def nova_senha():
    dados = validar(RedefinirSenhaSchema, _json())
    redefinir_senha(dados.login, dados.codigo, dados.nova_senha)
    return {"message": "Senha alterada. Entre com a senha nova."}


# ==========================================================
# VERIFICACAO EM DUAS ETAPAS (aplicativo autenticador)
# ==========================================================
@bp.get("/2fa")
@login_required
def situacao_2fa():
    return {"dois_fatores": dois_fatores.situacao(g.usuario)}


@bp.post("/2fa/iniciar")
@login_required
def iniciar_2fa():
    return dois_fatores.iniciar(g.usuario)


@bp.post("/2fa/ativar")
@login_required
def ativar_2fa():
    dados = validar(SenhaECodigoSchema, _json())
    codigos = dois_fatores.ativar(g.usuario, dados.senha, dados.codigo)
    return {"usuario": g.usuario.to_dict(privado=True), "codigos_reserva": codigos,
            "dois_fatores": dois_fatores.situacao(g.usuario)}


@bp.post("/2fa/desativar")
@login_required
def desativar_2fa():
    dados = validar(SenhaECodigoSchema, _json())
    usuario = dois_fatores.desativar(g.usuario, dados.senha, dados.codigo)
    return {"usuario": usuario.to_dict(privado=True), "dois_fatores": dois_fatores.situacao(usuario)}


@bp.post("/2fa/codigos-reserva")
@login_required
def novos_codigos_2fa():
    dados = validar(SenhaECodigoSchema, _json())
    codigos = dois_fatores.novos_codigos(g.usuario, dados.senha, dados.codigo)
    return {"codigos_reserva": codigos, "dois_fatores": dois_fatores.situacao(g.usuario)}


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
    dados = validar(PerfilSchema, _json())
    usuario = atualizar_perfil(g.usuario, dados)
    corpo = {"usuario": usuario.to_dict(privado=True)}
    if dados.nova_senha is not None:
        corpo["token"] = gerar_token(usuario)   # o token antigo deixou de valer com a troca de senha
    return corpo


# ==========================================================
# FOTO DE PERFIL
# PUT recebe o arquivo em multipart/form-data (campo "foto"); a imagem e
# servida em /api/fotos/<token>, sem login, porque a tag <img> nao envia o
# cabecalho Authorization. O token aleatorio faz o papel da senha do link.
# ==========================================================
@bp.put("/me/foto")
@login_required
def enviar_foto():
    arquivo = request.files.get("foto")
    usuario = salvar_foto(g.usuario, arquivo.read() if arquivo else b"")
    return {"usuario": usuario.to_dict(privado=True)}


@bp.delete("/me/foto")
@login_required
def apagar_foto():
    return {"usuario": remover_foto(g.usuario).to_dict(privado=True)}


@bp_fotos.get("/<token>")
def ver_foto(token):
    foto = buscar_foto(token)
    return Response(foto.dados, mimetype=foto.mime, headers={
        # o endereco muda a cada foto nova, entao o navegador pode guardar por 1 ano
        "Cache-Control": "private, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
    })


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
