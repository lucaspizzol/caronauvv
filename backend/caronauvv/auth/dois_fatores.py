"""
VERIFICACAO EM DUAS ETAPAS (2FA) COM APLICATIVO AUTENTICADOR

Com ela ligada, entrar na conta pede duas provas: a senha (algo que o aluno
sabe) e o codigo de 6 numeros do aplicativo (algo que o aluno tem: o celular).

Passo a passo:
1. iniciar():  gera o segredo e o endereco otpauth:// (vira QR Code na tela);
2. ativar():   o aluno confirma a senha e digita o codigo do aplicativo; se bater, a protecao
               liga e ele recebe 8 codigos de reserva (para o dia em que ficar sem o celular);
3. login:      /login confere a senha e devolve um "desafio" assinado que vale 5 min;
               /login/2fa recebe o desafio + o codigo e so entao entrega o token;
4. desativar() e novos_codigos() pedem a senha e um codigo.

Protecoes: cada codigo vale uma vez, 5 erros seguidos bloqueiam por 10 minutos
(contador no banco, entao vale tambem na hospedagem serverless) e os codigos de
reserva sao guardados como HMAC-SHA256, nunca em texto.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from . import totp
from .models import CodigoReserva, Usuario

QTD_CODIGOS_RESERVA = 8
# Sem 0/O e 1/I/L, que as pessoas confundem ao copiar do papel
ALFABETO_RESERVA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


# ==========================================================
# CODIGOS DE RESERVA
# ==========================================================
def _limpar_reserva(codigo: str) -> str:
    return "".join(c for c in str(codigo or "").upper() if c.isalnum())


def _hash_reserva(usuario: Usuario, codigo: str) -> str:
    chave = current_app.config["SECRET_KEY"].encode()
    return hmac.new(chave, f"reserva:{usuario.id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def _gerar_codigos_reserva(usuario: Usuario) -> list[str]:
    usuario.codigos_reserva.clear()   # delete-orphan: os antigos sao apagados
    codigos = []
    for _ in range(QTD_CODIGOS_RESERVA):
        codigo = "".join(secrets.choice(ALFABETO_RESERVA) for _ in range(8))
        usuario.codigos_reserva.append(CodigoReserva(codigo_hash=_hash_reserva(usuario, codigo)))
        codigos.append(f"{codigo[:4]}-{codigo[4:]}")
    return codigos


def codigos_restantes(usuario: Usuario) -> int:
    return sum(1 for c in usuario.codigos_reserva if c.usado_em is None)


# ==========================================================
# LIGAR
# ==========================================================
def iniciar(usuario: Usuario) -> dict:
    if usuario.totp_ativo:
        raise ApiError("A verificação em duas etapas já está ativa.")
    usuario.totp_segredo = totp.novo_segredo()
    db.session.commit()
    return {
        "segredo": usuario.totp_segredo,
        "uri": totp.uri_otpauth(usuario.totp_segredo, usuario.email),
    }


def ativar(usuario: Usuario, senha: str, codigo: str) -> list[str]:
    if usuario.totp_ativo:
        raise ApiError("A verificação em duas etapas já está ativa.")
    if not usuario.totp_segredo:
        raise ApiError("Comece a configuração de novo para gerar o QR Code.")
    # Pede a senha de novo: quem pegou um celular desbloqueado nao consegue trancar o dono para fora
    if not usuario.check_senha(senha or ""):
        raise ApiError("Senha incorreta.", 403, campos={"senha": "Senha incorreta."})
    passo = totp.verificar(usuario.totp_segredo, codigo)
    if passo is None:
        raise ApiError(
            "Código incorreto. Confira se o horário do celular está automático e digite o código atual.",
            campos={"codigo": "Código incorreto."},
        )
    usuario.totp_ativo = True
    usuario.totp_ativado_em = datetime.now()
    usuario.totp_ultimo_passo = passo
    usuario.totp_falhas = 0
    usuario.totp_bloqueado_ate = None
    codigos = _gerar_codigos_reserva(usuario)
    _avisar(usuario, "Verificação em duas etapas ativada",
            "Agora o login pede também o código do seu aplicativo autenticador.")
    db.session.commit()
    return codigos


# ==========================================================
# CONFERIR O SEGUNDO FATOR (login e acoes sensiveis)
# ==========================================================
def conferir_segundo_fator(usuario: Usuario, codigo: str, status_erro: int = 401) -> str:
    """
    Aceita o codigo do aplicativo ou um codigo de reserva. Devolve "app" ou "reserva".
    status_erro: 401 no login (ainda nao entrou); 400 para quem ja esta logado, porque
    o frontend trata 401 como "sessao acabou" e mandaria o aluno de volta ao login.
    """
    cfg = current_app.config
    agora = datetime.now()
    if usuario.totp_bloqueado_ate and usuario.totp_bloqueado_ate > agora:
        minutos = max(1, round((usuario.totp_bloqueado_ate - agora).total_seconds() / 60))
        raise ApiError(f"Muitos códigos errados. Tente de novo em {minutos} min.", 429)

    metodo = None
    passo = totp.verificar(usuario.totp_segredo or "", codigo, depois_do_passo=usuario.totp_ultimo_passo) \
        if usuario.totp_segredo else None
    if passo is not None:
        usuario.totp_ultimo_passo = passo   # este codigo nao vale mais
        metodo = "app"
    else:
        limpo = _limpar_reserva(codigo)
        if len(limpo) == 8:
            esperado = _hash_reserva(usuario, limpo)
            for reserva in usuario.codigos_reserva:
                if reserva.usado_em is None and hmac.compare_digest(reserva.codigo_hash, esperado):
                    reserva.usado_em = agora
                    metodo = "reserva"
                    break

    if metodo is None:
        usuario.totp_falhas += 1
        if usuario.totp_falhas >= cfg["DOIS_FATORES_MAX_TENTATIVAS"]:
            usuario.totp_falhas = 0
            usuario.totp_bloqueado_ate = agora + timedelta(minutes=cfg["DOIS_FATORES_BLOQUEIO_MIN"])
        db.session.commit()
        raise ApiError("Código incorreto.", status_erro, campos={"codigo": "Código incorreto."})

    usuario.totp_falhas = 0
    usuario.totp_bloqueado_ate = None
    db.session.commit()
    return metodo


def _exigir_senha_e_codigo(usuario: Usuario, senha: str, codigo: str) -> None:
    if not usuario.totp_ativo:
        raise ApiError("A verificação em duas etapas não está ativa.")
    if not usuario.check_senha(senha or ""):
        raise ApiError("Senha incorreta.", 403, campos={"senha": "Senha incorreta."})
    conferir_segundo_fator(usuario, codigo, status_erro=400)


# ==========================================================
# DESLIGAR / NOVOS CODIGOS DE RESERVA
# ==========================================================
def _limpar(usuario: Usuario) -> None:
    usuario.totp_ativo = False
    usuario.totp_segredo = None
    usuario.totp_ativado_em = None
    usuario.totp_ultimo_passo = None
    usuario.totp_falhas = 0
    usuario.totp_bloqueado_ate = None
    usuario.codigos_reserva.clear()


def desativar(usuario: Usuario, senha: str, codigo: str) -> Usuario:
    _exigir_senha_e_codigo(usuario, senha, codigo)
    _limpar(usuario)
    _avisar(usuario, "Verificação em duas etapas desativada",
            "O login voltou a pedir só a senha. Se não foi você, troque a senha agora.")
    db.session.commit()
    return usuario


def novos_codigos(usuario: Usuario, senha: str, codigo: str) -> list[str]:
    _exigir_senha_e_codigo(usuario, senha, codigo)
    codigos = _gerar_codigos_reserva(usuario)
    db.session.commit()
    return codigos


def resetar_pelo_admin(usuario: Usuario) -> Usuario:
    """Aluno perdeu o celular e os codigos de reserva: a administracao desliga a protecao."""
    if not usuario.totp_ativo:
        raise ApiError("Este usuário não usa a verificação em duas etapas.")
    _limpar(usuario)
    _avisar(usuario, "Verificação em duas etapas desativada",
            "A administração desligou o autenticador da sua conta. Você pode ativar de novo no perfil.")
    db.session.commit()
    return usuario


def situacao(usuario: Usuario) -> dict:
    return {
        "ativo": usuario.totp_ativo,
        "ativado_em": usuario.totp_ativado_em.isoformat(timespec="minutes") if usuario.totp_ativado_em else None,
        "codigos_restantes": codigos_restantes(usuario) if usuario.totp_ativo else 0,
    }


def _avisar(usuario: Usuario, titulo: str, texto: str) -> None:
    from caronauvv.notificacoes.services import notificar
    notificar(usuario, "seguranca_conta", titulo, texto)


# ==========================================================
# DESAFIO: liga a 1a etapa (senha certa) a 2a (codigo), sem guardar nada no servidor
# ==========================================================
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="caronauvv-2fa")


def gerar_desafio(usuario: Usuario) -> str:
    return _serializer().dumps({"id": usuario.id, "v": usuario.sessao_versao})


def usuario_do_desafio(desafio: str) -> Usuario:
    expirou = ApiError("O tempo para digitar o código acabou. Entre com a senha de novo.", 401)
    try:
        dados = _serializer().loads(desafio, max_age=current_app.config["DOIS_FATORES_DESAFIO_SEG"])
    except SignatureExpired:
        raise expirou
    except BadSignature:
        raise ApiError("Pedido inválido. Entre com a senha de novo.", 401)
    usuario = db.session.get(Usuario, dados.get("id"))
    if usuario is None or not usuario.is_active or not usuario.totp_ativo:
        raise ApiError("Pedido inválido. Entre com a senha de novo.", 401)
    if dados.get("v") != usuario.sessao_versao:   # a senha mudou no meio do caminho
        raise expirou
    return usuario
