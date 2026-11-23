"""
Schemas (Pydantic) dos formularios de conta: cadastro, login, perfil,
preferencias, veiculos, contatos de confianca e verificacao de e-mail.
Uso nas rotas: dados = validar(CadastroSchema, request.get_json())
"""
import re
from typing import Literal

from flask import current_app
from pydantic import Field, field_validator

from caronauvv.validacao import Digitos, Schema, TextoOpcional

from .models import ENERGIAS, NIVEIS_CONVERSA

SENHA_MINIMA = 6
PLACA_REGEX = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # ABC1234 ou Mercosul ABC1D23
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _telefone(valor: str) -> str:
    # DDD + numero: 10 (fixo) ou 11 (celular) digitos; aceita +55 na frente
    if valor.startswith("55") and len(valor) in (12, 13):
        valor = valor[2:]
    if len(valor) not in (10, 11):
        raise ValueError("Informe o telefone com DDD, ex.: (27) 99999-0000.")
    return valor


def dominios_permitidos() -> tuple[str, ...]:
    return tuple(current_app.config.get("DOMINIOS_EMAIL", ("uvv.br",)))


# ==========================================================
# CADASTRO
# ==========================================================
class CadastroSchema(Schema):
    nome: str = Field(min_length=1, max_length=150)
    matricula: str = Field(min_length=1, max_length=20)
    email: str = Field(min_length=1, max_length=255)
    telefone: Digitos = Field(min_length=1)
    bairro: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=128)
    curso: TextoOpcional = Field(default=None, max_length=120)

    @field_validator("matricula")
    @classmethod
    def _matricula(cls, v: str) -> str:
        if not re.fullmatch(r"\d{5,12}", v):
            raise ValueError("A matrícula tem de 5 a 12 números.")
        return v

    @field_validator("email")
    @classmethod
    def _email_institucional(cls, v: str) -> str:
        v = v.lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("E-mail inválido.")
        dominio = v.rsplit("@", 1)[1]
        permitidos = dominios_permitidos()
        # aceita o dominio exato (uvv.br) e subdominios (aluno.uvv.br)
        if not any(dominio == d or dominio.endswith("." + d) for d in permitidos):
            raise ValueError(f"Use seu e-mail institucional (@{permitidos[0]}). Só alunos da UVV podem entrar.")
        return v

    @field_validator("telefone")
    @classmethod
    def _tel(cls, v: str) -> str:
        return _telefone(v)

    @field_validator("senha")
    @classmethod
    def _senha(cls, v: str) -> str:
        if len(v) < SENHA_MINIMA:
            raise ValueError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
        return v


class LoginSchema(Schema):
    login: str = Field(min_length=1, max_length=255)
    senha: str = Field(min_length=1, max_length=128)


class SegundaEtapaSchema(Schema):
    """Segunda etapa do login: o desafio devolvido pelo /login + o codigo do aplicativo."""
    desafio: str = Field(min_length=1, max_length=500)
    codigo: str = Field(min_length=1, max_length=20)   # 6 numeros do app ou codigo de reserva (ABCD-EFGH)


class SenhaECodigoSchema(Schema):
    """Ligar, desligar e gerar codigos da verificacao em duas etapas pedem a senha e um codigo."""
    senha: str = Field(min_length=1, max_length=128)
    codigo: str = Field(min_length=1, max_length=20)


class EsqueciSenhaSchema(Schema):
    login: str = Field(min_length=1, max_length=255)   # e-mail ou matricula


class CodigoSchema(Schema):
    codigo: Digitos = Field(min_length=1)

    @field_validator("codigo")
    @classmethod
    def _seis_digitos(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError("O código tem 6 números.")
        return v


class RedefinirSenhaSchema(Schema):
    login: str = Field(min_length=1, max_length=255)
    codigo: Digitos = Field(min_length=1)
    nova_senha: str = Field(min_length=1, max_length=128)

    @field_validator("codigo")
    @classmethod
    def _seis_digitos(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError("O código tem 6 números.")
        return v

    @field_validator("nova_senha")
    @classmethod
    def _senha(cls, v: str) -> str:
        if len(v) < SENHA_MINIMA:
            raise ValueError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
        return v


# ==========================================================
# PERFIL (PUT /api/auth/me): todos os campos sao opcionais,
# mas os obrigatorios do cadastro nao podem ficar vazios.
# ==========================================================
class PerfilSchema(Schema):
    nome: str | None = Field(default=None, min_length=1, max_length=150)
    telefone: Digitos | None = Field(default=None, min_length=1)
    bairro: str | None = Field(default=None, min_length=1, max_length=100)
    curso: TextoOpcional = Field(default=None, max_length=120)
    endereco: TextoOpcional = Field(default=None, max_length=255)
    chave_pix: TextoOpcional = Field(default=None, max_length=150)
    bio: TextoOpcional = Field(default=None, max_length=300)
    pref_conversa: Literal[NIVEIS_CONVERSA] | None = None  # type: ignore[valid-type]
    pref_musica: bool | None = None
    pref_animais: bool | None = None
    pref_fumar: bool | None = None
    # troca de senha
    senha_atual: str | None = None
    nova_senha: str | None = None

    @field_validator("telefone")
    @classmethod
    def _tel(cls, v: str | None) -> str | None:
        return None if v is None else _telefone(v)

    @field_validator("nome", "telefone", "bairro", mode="before")
    @classmethod
    def _nao_vazio(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("Este campo não pode ficar vazio.")
        return v

    @field_validator("nova_senha")
    @classmethod
    def _nova_senha(cls, v: str | None) -> str | None:
        if v is not None and len(v) < SENHA_MINIMA:
            raise ValueError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
        return v


# ==========================================================
# VEICULO
# ==========================================================
def _placa(valor: str) -> str:
    placa = re.sub(r"[\s-]", "", valor).upper()
    if not PLACA_REGEX.match(placa):
        raise ValueError("Placa inválida (ex.: ABC1234 ou ABC1D23).")
    return placa


class VeiculoSchema(Schema):
    modelo: str = Field(min_length=1, max_length=80)
    cor: str = Field(min_length=1, max_length=30)
    placa: str = Field(min_length=1, max_length=10)
    energia: Literal[ENERGIAS] = "flex"  # type: ignore[valid-type]
    consumo_km: float | None = Field(default=None, gt=0, le=60)   # km/l (eletrico: km/kWh)

    @field_validator("placa")
    @classmethod
    def _p(cls, v: str) -> str:
        return _placa(v)


class VeiculoEdicaoSchema(Schema):
    modelo: str | None = Field(default=None, min_length=1, max_length=80)
    cor: str | None = Field(default=None, min_length=1, max_length=30)
    placa: str | None = Field(default=None, min_length=1, max_length=10)
    energia: Literal[ENERGIAS] | None = None  # type: ignore[valid-type]
    consumo_km: float | None = Field(default=None, gt=0, le=60)

    @field_validator("placa")
    @classmethod
    def _p(cls, v: str | None) -> str | None:
        return None if v is None else _placa(v)

    @field_validator("modelo", "cor", "placa", "energia", mode="before")
    @classmethod
    def _nao_vazio(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("Este campo não pode ficar vazio.")
        return v


# ==========================================================
# CONTATO DE CONFIANCA (recebe o link da viagem)
# ==========================================================
class ContatoSchema(Schema):
    nome: str = Field(min_length=1, max_length=100)
    telefone: Digitos = Field(min_length=1)

    @field_validator("telefone")
    @classmethod
    def _tel(cls, v: str) -> str:
        return _telefone(v)
