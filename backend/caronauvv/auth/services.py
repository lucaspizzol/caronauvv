import re
from datetime import datetime

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import or_

from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from .models import Usuario, Veiculo


CAMPOS_OBRIGATORIOS = ("matricula", "email", "nome", "telefone", "bairro", "senha")
CAMPOS_PERFIL_OBRIGATORIOS = ("nome", "telefone", "bairro")
CAMPOS_PERFIL_OPCIONAIS = ("curso", "endereco", "foto_url", "chave_pix")
SENHA_MINIMA = 6


def _texto(dados: dict, campo: str) -> str:
    valor = dados.get(campo)
    return str(valor).strip() if valor is not None else ""


def _validar_senha(senha: str) -> None:
    if len(senha) < SENHA_MINIMA:
        raise ApiError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")


# ==========================================================
# CADASTRO
# ==========================================================
def cadastrar_usuario(dados: dict) -> Usuario:
    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if not _texto(dados, campo)]
    if faltando:
        raise ApiError(f"Campos obrigatórios: {', '.join(faltando)}.")

    matricula = _texto(dados, "matricula")
    email = _texto(dados, "email").lower()
    senha = str(dados["senha"])

    if "@" not in email:
        raise ApiError("E-mail inválido.")
    _validar_senha(senha)

    existente = db.session.scalar(
        db.select(Usuario).where(or_(Usuario.matricula == matricula, Usuario.email == email))
    )
    if existente:
        raise ApiError("Já existe um usuário com essa matrícula ou e-mail.", 409)

    usuario = Usuario(
        matricula=matricula,
        email=email,
        nome=_texto(dados, "nome"),
        telefone=_texto(dados, "telefone"),
        bairro=_texto(dados, "bairro"),
        curso=_texto(dados, "curso") or None,
    )
    usuario.set_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    return usuario


# ==========================================================
# LOGIN (por e-mail ou matricula)
# ==========================================================
def autenticar(login: str, senha: str) -> Usuario:
    login = (login or "").strip()
    usuario = db.session.scalar(
        db.select(Usuario).where(or_(Usuario.email == login.lower(), Usuario.matricula == login))
    )
    if usuario is None or not usuario.check_senha(senha or ""):
        raise ApiError("Login ou senha inválidos.", 401)
    if not usuario.is_active:
        raise ApiError("Conta desativada.", 403)
    usuario.ultimo_login_em = datetime.now()
    db.session.commit()
    return usuario


# ==========================================================
# TOKEN (assinado com a SECRET_KEY via itsdangerous)
# O token nao fica salvo no banco: logout = o frontend descarta o token.
# ==========================================================
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="caronauvv-auth")


def gerar_token(usuario: Usuario) -> str:
    return _serializer().dumps({"id": usuario.id})


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
    return usuario


# ==========================================================
# PERFIL
# ==========================================================
def atualizar_perfil(usuario: Usuario, dados: dict) -> Usuario:
    for campo in CAMPOS_PERFIL_OBRIGATORIOS:
        if campo in dados:
            valor = _texto(dados, campo)
            if not valor:
                raise ApiError(f"O campo {campo} não pode ficar vazio.")
            setattr(usuario, campo, valor)

    for campo in CAMPOS_PERFIL_OPCIONAIS:
        if campo in dados:
            setattr(usuario, campo, _texto(dados, campo) or None)

    if "nova_senha" in dados:
        if not usuario.check_senha(str(dados.get("senha_atual") or "")):
            raise ApiError("Senha atual incorreta.", 403)
        nova_senha = str(dados["nova_senha"] or "")
        _validar_senha(nova_senha)
        usuario.set_senha(nova_senha)

    db.session.commit()
    return usuario


# ==========================================================
# VEICULOS DO MOTORISTA
# ==========================================================
PLACA_REGEX = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # ABC1234 ou Mercosul ABC1D23
STATUS_CARONA_EM_ABERTO = ("ativa", "lotada", "em_andamento")


def _placa(valor) -> str:
    placa = re.sub(r"[\s-]", "", str(valor or "")).upper()
    if not PLACA_REGEX.match(placa):
        raise ApiError("Placa inválida (ex.: ABC1234 ou ABC1D23).")
    return placa


def buscar_veiculo(veiculo_id: int, usuario: Usuario) -> Veiculo:
    veiculo = db.session.get(Veiculo, veiculo_id)
    if veiculo is None or veiculo.usuario_id != usuario.id:
        raise ApiError("Veículo não encontrado.", 404)
    return veiculo


def _aplicar_veiculo(veiculo: Veiculo, dados: dict, obrigatorio: bool) -> None:
    for campo in ("modelo", "cor"):
        if obrigatorio or campo in dados:
            valor = _texto(dados, campo)
            if not valor:
                raise ApiError(f"O campo {campo} não pode ficar vazio.")
            setattr(veiculo, campo, valor)

    if obrigatorio or "placa" in dados:
        placa = _placa(dados.get("placa"))
        outro = db.session.scalar(db.select(Veiculo).where(Veiculo.placa == placa))
        if outro is not None and outro.id != veiculo.id:
            raise ApiError("Já existe um veículo com essa placa.", 409)
        veiculo.placa = placa


def cadastrar_veiculo(usuario: Usuario, dados: dict) -> Veiculo:
    veiculo = Veiculo(usuario_id=usuario.id)
    _aplicar_veiculo(veiculo, dados, obrigatorio=True)
    db.session.add(veiculo)
    db.session.commit()
    return veiculo


def editar_veiculo(veiculo: Veiculo, dados: dict) -> Veiculo:
    _aplicar_veiculo(veiculo, dados, obrigatorio=False)
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
