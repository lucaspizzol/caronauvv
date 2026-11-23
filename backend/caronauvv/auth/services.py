import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import or_

from caronauvv.email import enviar_email
from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from .models import ContatoConfianca, Usuario, Veiculo
from .schemas import CadastroSchema, ContatoSchema, PerfilSchema, VeiculoEdicaoSchema, VeiculoSchema

STATUS_CARONA_EM_ABERTO = ("ativa", "lotada", "em_andamento")
MAX_CONTATOS = 5
MAX_TENTATIVAS_CODIGO = 5


# ==========================================================
# CADASTRO (os dados ja chegam validados pelo CadastroSchema)
# ==========================================================
def cadastrar_usuario(dados: CadastroSchema) -> tuple[Usuario, str]:
    existente = db.session.scalar(
        db.select(Usuario).where(or_(Usuario.matricula == dados.matricula, Usuario.email == dados.email))
    )
    if existente:
        raise ApiError("Já existe um usuário com essa matrícula ou e-mail.", 409)

    usuario = Usuario(
        matricula=dados.matricula,
        email=dados.email,
        nome=dados.nome,
        telefone=dados.telefone,
        bairro=dados.bairro,
        curso=dados.curso,
    )
    usuario.set_senha(dados.senha)
    db.session.add(usuario)
    codigo = _novo_codigo(usuario)
    db.session.commit()
    _enviar_codigo(usuario, codigo)
    return usuario, codigo


# ==========================================================
# VERIFICACAO DO E-MAIL UVV (codigo de 6 digitos, como no BlaBlaCar)
# O codigo nunca fica salvo em texto: guardamos um HMAC-SHA256 dele
# (assinado com a SECRET_KEY). Vence em 30 min e aceita 5 tentativas.
# ==========================================================
def _hash_codigo(usuario: Usuario, codigo: str) -> str:
    chave = current_app.config["SECRET_KEY"].encode()
    return hmac.new(chave, f"{usuario.email}:{codigo}".encode(), hashlib.sha256).hexdigest()


def _novo_codigo(usuario: Usuario) -> str:
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.codigo_verificacao_hash = _hash_codigo(usuario, codigo)
    usuario.codigo_tentativas = 0
    usuario.codigo_expira_em = datetime.now() + timedelta(minutes=current_app.config["CODIGO_VALIDADE_MIN"])
    return codigo


def _enviar_codigo(usuario: Usuario, codigo: str) -> None:
    enviar_email(
        usuario.email,
        "CaronaUVV - seu código de verificação",
        f"Olá, {usuario.nome.split()[0]}! Seu código para confirmar o e-mail no CaronaUVV é {codigo}. "
        f"Ele vale por {current_app.config['CODIGO_VALIDADE_MIN']} minutos.",
    )


def reenviar_codigo(usuario: Usuario) -> str:
    if usuario.email_verificado:
        raise ApiError("Seu e-mail já está confirmado.")
    codigo = _novo_codigo(usuario)
    db.session.commit()
    _enviar_codigo(usuario, codigo)
    return codigo


def verificar_email(usuario: Usuario, codigo: str) -> Usuario:
    if usuario.email_verificado:
        return usuario
    if not usuario.codigo_verificacao_hash or not usuario.codigo_expira_em:
        raise ApiError("Peça um novo código.")
    if usuario.codigo_expira_em < datetime.now():
        raise ApiError("O código venceu. Peça um novo.")
    if usuario.codigo_tentativas >= MAX_TENTATIVAS_CODIGO:
        raise ApiError("Muitas tentativas erradas. Peça um novo código.", 429)
    if not hmac.compare_digest(usuario.codigo_verificacao_hash, _hash_codigo(usuario, codigo)):
        usuario.codigo_tentativas += 1
        db.session.commit()
        raise ApiError("Código incorreto.")
    usuario.email_verificado = True
    usuario.codigo_verificacao_hash = None
    usuario.codigo_expira_em = None
    db.session.commit()
    return usuario


def exigir_email_verificado(usuario: Usuario, acao: str) -> None:
    """Regra de confianca: so quem confirmou o e-mail UVV pode oferecer ou pedir carona."""
    if not usuario.email_verificado:
        raise ApiError(f"Confirme seu e-mail UVV antes de {acao}.", 403)


def solicitar_verificacao_perfil(usuario: Usuario) -> Usuario:
    """O aluno pede o selo "Perfil verificado"; o admin confere a matricula e aprova."""
    exigir_email_verificado(usuario, "pedir a verificação do perfil")
    if usuario.verificado:
        raise ApiError("Seu perfil já é verificado.")
    usuario.verificacao_solicitada_em = datetime.now()
    db.session.commit()
    return usuario


# ==========================================================
# LOGIN (por e-mail ou matricula) com protecao contra forca bruta:
# depois de N senhas erradas em X minutos, o login fica bloqueado.
# (Em memoria, por app: basta para um servidor. Com varios, usar Redis.)
# ==========================================================
def _falhas_login() -> dict[str, deque]:
    return current_app.extensions.setdefault("caronauvv_falhas_login", defaultdict(deque))


def _bloqueado(chave: str) -> bool:
    janela = current_app.config["LOGIN_JANELA_MIN"] * 60
    falhas = _falhas_login()[chave]
    while falhas and falhas[0] < time.monotonic() - janela:
        falhas.popleft()
    return len(falhas) >= current_app.config["LOGIN_MAX_TENTATIVAS"]


def autenticar(login: str, senha: str) -> Usuario:
    login = (login or "").strip()
    chave = login.lower()
    if _bloqueado(chave):
        raise ApiError(
            f"Muitas tentativas erradas. Espere {current_app.config['LOGIN_JANELA_MIN']} minutos e tente de novo.", 429
        )
    usuario = db.session.scalar(
        db.select(Usuario).where(or_(Usuario.email == chave, Usuario.matricula == login))
    )
    if usuario is None or not usuario.check_senha(senha or ""):
        _falhas_login()[chave].append(time.monotonic())
        raise ApiError("Login ou senha inválidos.", 401)
    if not usuario.is_active:
        raise ApiError("Conta suspensa. Procure a administração do CaronaUVV.", 403)
    _falhas_login().pop(chave, None)
    usuario.ultimo_login_em = datetime.now()
    db.session.commit()
    return usuario


# ==========================================================
# ESQUECI MINHA SENHA
# 1) /esqueci-senha: manda um codigo de 6 numeros para o e-mail da conta
# 2) /redefinir-senha: codigo certo + senha nova
# A resposta do passo 1 e sempre a mesma, exista a conta ou nao, para ninguem
# descobrir por ali quem tem cadastro. O codigo vence em 30 min, aceita 5
# tentativas e so pode ser pedido de novo depois de 1 minuto.
# ==========================================================
INTERVALO_REENVIO_SEG = 60


def _por_login(login: str) -> Usuario | None:
    login = (login or "").strip()
    return db.session.scalar(
        db.select(Usuario).where(or_(Usuario.email == login.lower(), Usuario.matricula == login))
    )


def _hash_reset(usuario: Usuario, codigo: str) -> str:
    chave = current_app.config["SECRET_KEY"].encode()
    return hmac.new(chave, f"reset:{usuario.id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def pedir_recuperacao(login: str) -> str | None:
    """Gera e envia o codigo. Devolve o codigo (para o modo de demonstracao) ou None."""
    usuario = _por_login(login)
    if usuario is None or not usuario.is_active:
        return None
    agora = datetime.now()
    if usuario.reset_enviado_em and (agora - usuario.reset_enviado_em).total_seconds() < INTERVALO_REENVIO_SEG:
        return None   # acabou de pedir: nao deixa encher a caixa de e-mail de ninguem
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.reset_codigo_hash = _hash_reset(usuario, codigo)
    usuario.reset_tentativas = 0
    usuario.reset_enviado_em = agora
    usuario.reset_expira_em = agora + timedelta(minutes=current_app.config["CODIGO_VALIDADE_MIN"])
    db.session.commit()
    enviar_email(
        usuario.email,
        "CaronaUVV - código para criar uma senha nova",
        f"Olá, {usuario.nome.split()[0]}! Seu código para criar uma senha nova no CaronaUVV é {codigo}. "
        f"Ele vale por {current_app.config['CODIGO_VALIDADE_MIN']} minutos. "
        "Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma.",
    )
    return codigo


def redefinir_senha(login: str, codigo: str, nova_senha: str) -> Usuario:
    usuario = _por_login(login)
    invalido = ApiError("Código incorreto ou vencido. Peça um novo código.", campos={"codigo": "Código incorreto ou vencido."})
    if usuario is None or not usuario.is_active or not usuario.reset_codigo_hash or not usuario.reset_expira_em:
        raise invalido
    if usuario.reset_expira_em < datetime.now():
        raise invalido
    if usuario.reset_tentativas >= MAX_TENTATIVAS_CODIGO:
        raise ApiError("Muitas tentativas erradas. Peça um novo código.", 429)
    if not hmac.compare_digest(usuario.reset_codigo_hash, _hash_reset(usuario, codigo)):
        usuario.reset_tentativas += 1
        db.session.commit()
        raise invalido

    usuario.set_senha(nova_senha)
    usuario.sessao_versao += 1            # quem estava logado com a senha antiga sai
    usuario.reset_codigo_hash = None
    usuario.reset_expira_em = None
    usuario.reset_tentativas = 0
    _falhas_login().pop(usuario.email, None)
    _falhas_login().pop(usuario.matricula, None)

    from caronauvv.notificacoes.services import notificar
    notificar(usuario, "seguranca_conta", "Senha alterada",
              "Sua senha foi trocada pelo \"esqueci minha senha\". Se não foi você, fale com a administração.")
    db.session.commit()
    enviar_email(
        usuario.email,
        "CaronaUVV - sua senha foi alterada",
        f"Olá, {usuario.nome.split()[0]}! A senha da sua conta no CaronaUVV acabou de ser alterada. "
        "Se não foi você, responda este e-mail ou procure a administração.",
    )
    return usuario


# ==========================================================
# TOKEN (assinado com a SECRET_KEY via itsdangerous)
# O token nao fica salvo no banco: logout = o frontend descarta o token.
# ==========================================================
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="caronauvv-auth")


def gerar_token(usuario: Usuario) -> str:
    # "v" = versao da sessao: trocar a senha sobe o numero e derruba os tokens antigos
    return _serializer().dumps({"id": usuario.id, "v": usuario.sessao_versao})


def usuario_do_token(token: str) -> Usuario:
    try:
        dados = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except SignatureExpired:
        raise ApiError("Sessão expirada, faça login novamente.", 401)
    except BadSignature:
        raise ApiError("Token inválido.", 401)

    usuario = db.session.get(Usuario, dados.get("id"))
    if usuario is None or not usuario.is_active:
        raise ApiError("Token inválido.", 401)
    if dados.get("v", 0) != usuario.sessao_versao:
        raise ApiError("Sua senha foi alterada. Faça login novamente.", 401)
    return usuario


# ==========================================================
# PERFIL
# ==========================================================
def atualizar_perfil(usuario: Usuario, dados: PerfilSchema) -> Usuario:
    campos = dados.preenchidos()
    senha_atual = campos.pop("senha_atual", None)
    nova_senha = campos.pop("nova_senha", None)

    for campo, valor in campos.items():
        setattr(usuario, campo, valor)

    if nova_senha is not None:
        if not usuario.check_senha(senha_atual or ""):
            raise ApiError("Senha atual incorreta.", 403)
        usuario.set_senha(nova_senha)
        usuario.sessao_versao += 1   # sai de todos os outros aparelhos (a rota devolve um token novo)

    db.session.commit()
    return usuario


def buscar_usuario(usuario_id: int) -> Usuario:
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None or not usuario.is_active:
        raise ApiError("Usuário não encontrado.", 404)
    return usuario


def perfil_publico(usuario: Usuario) -> dict:
    """Perfil que qualquer aluno ve antes de pedir vaga (reputacao estilo BlaBlaCar)."""
    from caronauvv.avaliacoes.services import avaliacoes_reveladas, reputacao

    return {
        **usuario.to_dict(),
        "reputacao": reputacao(usuario),
        "avaliacoes": [a.to_dict() for a in avaliacoes_reveladas(usuario, limite=10)],
        "veiculos": [v.to_dict() for v in usuario.veiculos],
    }


# ==========================================================
# VEICULOS DO MOTORISTA
# ==========================================================
def buscar_veiculo(veiculo_id: int, usuario: Usuario) -> Veiculo:
    veiculo = db.session.get(Veiculo, veiculo_id)
    if veiculo is None or veiculo.usuario_id != usuario.id:
        raise ApiError("Veículo não encontrado.", 404)
    return veiculo


def _aplicar_veiculo(veiculo: Veiculo, campos: dict) -> None:
    if "placa" in campos:
        outro = db.session.scalar(db.select(Veiculo).where(Veiculo.placa == campos["placa"]))
        if outro is not None and outro.id != veiculo.id:
            raise ApiError("Já existe um veículo com essa placa.", 409)
    for campo, valor in campos.items():
        setattr(veiculo, campo, valor)


def cadastrar_veiculo(usuario: Usuario, dados: VeiculoSchema) -> Veiculo:
    veiculo = Veiculo(usuario_id=usuario.id)
    _aplicar_veiculo(veiculo, dados.model_dump())
    db.session.add(veiculo)
    db.session.commit()
    return veiculo


def editar_veiculo(veiculo: Veiculo, dados: VeiculoEdicaoSchema) -> Veiculo:
    _aplicar_veiculo(veiculo, dados.preenchidos())
    db.session.commit()
    return veiculo


def remover_veiculo(veiculo: Veiculo) -> None:
    from caronauvv.caronas.models import Carona

    caronas = list(db.session.scalars(db.select(Carona).where(Carona.veiculo_id == veiculo.id)))
    if any(c.status in STATUS_CARONA_EM_ABERTO for c in caronas):
        raise ApiError("Este veículo está em uma carona em aberto; cancele ou troque o veículo antes.")
    # Caronas antigas ficam sem veiculo em vez de apontar para um registro apagado
    for carona in caronas:
        carona.veiculo_id = None
    db.session.delete(veiculo)
    db.session.commit()


# ==========================================================
# CONTATOS DE CONFIANCA ("Mae", "Julia")
# ==========================================================
def adicionar_contato(usuario: Usuario, dados: ContatoSchema) -> ContatoConfianca:
    if len(usuario.contatos_confianca) >= MAX_CONTATOS:
        raise ApiError(f"Você pode ter no máximo {MAX_CONTATOS} contatos de confiança.")
    contato = ContatoConfianca(usuario=usuario, nome=dados.nome, telefone=dados.telefone)
    db.session.add(contato)
    db.session.commit()
    return contato


def remover_contato(usuario: Usuario, contato_id: int) -> None:
    contato = db.session.get(ContatoConfianca, contato_id)
    if contato is None or contato.usuario_id != usuario.id:
        raise ApiError("Contato não encontrado.", 404)
    db.session.delete(contato)
    db.session.commit()
