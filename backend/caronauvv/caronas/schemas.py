"""
Schemas (Pydantic) dos formularios de carona e de pedido de vaga.
Regras que dependem do banco (vagas ja aceitas, dono do veiculo, teto do
rateio nas configuracoes) ficam no services.py.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from caronauvv.validacao import Bairro, Schema, TextoOpcional

from caronauvv.auth.models import ENERGIAS

from .models import SENTIDOS

VAGAS_MIN, VAGAS_MAX = 1, 6


def _sem_fuso(valor: datetime) -> datetime:
    # O banco guarda horario local sem fuso
    if valor.tzinfo is not None:
        return valor.astimezone().replace(tzinfo=None)
    return valor


# ==========================================================
# CARONA - edicao (PUT): todos os campos opcionais
# ==========================================================
class CaronaEdicaoSchema(Schema):
    sentido: Literal[SENTIDOS] | None = None  # type: ignore[valid-type]
    bairro_origem: Bairro | None = Field(default=None, min_length=1, max_length=100)
    endereco_origem: str | None = Field(default=None, min_length=1, max_length=255)
    destino: str | None = Field(default=None, min_length=1, max_length=255)
    data_hora_saida: datetime | None = None
    vagas: int | None = Field(default=None, ge=VAGAS_MIN, le=VAGAS_MAX)
    valor_por_passageiro: Decimal | None = Field(default=None, ge=0, le=999)
    reserva_automatica: bool | None = None
    veiculo_id: int | None = None
    observacoes: TextoOpcional = Field(default=None, max_length=300)
    origem_lat: float | None = Field(default=None, ge=-90, le=90)
    origem_lng: float | None = Field(default=None, ge=-180, le=180)
    distancia_km: float | None = Field(default=None, ge=0, le=500)
    duracao_min: int | None = Field(default=None, ge=0, le=600)
    # Calculo do rateio: mandar o adicional liga o calculo pelo combustivel
    # (o servidor calcula o valor; o valor_por_passageiro enviado e ignorado)
    energia: Literal[ENERGIAS] | None = None  # type: ignore[valid-type]
    consumo_km: float | None = Field(default=None, gt=0, le=60)
    adicional_por_passageiro: Decimal | None = Field(default=None, ge=0, le=999)

    @field_validator("bairro_origem", "endereco_origem", "destino", "data_hora_saida", "vagas", mode="before")
    @classmethod
    def _nao_vazio(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("Este campo não pode ficar vazio.")
        return v

    @field_validator("data_hora_saida")
    @classmethod
    def _fuso(cls, v: datetime | None) -> datetime | None:
        return None if v is None else _sem_fuso(v)


# ==========================================================
# CARONA - criacao (POST): os campos principais passam a ser obrigatorios
# ==========================================================
class CaronaNovaSchema(CaronaEdicaoSchema):
    bairro_origem: Bairro = Field(min_length=1, max_length=100)
    endereco_origem: str = Field(min_length=1, max_length=255)
    data_hora_saida: datetime
    vagas: int = Field(ge=VAGAS_MIN, le=VAGAS_MAX)


# ==========================================================
# PEDIDO DE VAGA / EMBARQUE / GPS
# ==========================================================
class PedidoVagaSchema(Schema):
    endereco_embarque: TextoOpcional = Field(default=None, max_length=255)
    mensagem: TextoOpcional = Field(default=None, max_length=300)


class PinSchema(Schema):
    pin: str = Field(min_length=1, max_length=4)

    @field_validator("pin")
    @classmethod
    def _quatro_digitos(cls, v: str) -> str:
        if not (len(v) == 4 and v.isdigit()):
            raise ValueError("O PIN tem 4 números.")
        return v


class PedidoCaronaSchema(Schema):
    """Entrar na fila do "Pedir carona"."""
    bairro: Bairro = Field(min_length=1, max_length=100)
    sentido: Literal[SENTIDOS] = "ida"  # type: ignore[valid-type]
    data: date
    hora_inicio: time
    hora_fim: time

    @field_validator("hora_fim")
    @classmethod
    def _faixa(cls, v: time, info) -> time:
        inicio = info.data.get("hora_inicio")
        if inicio is not None and v <= inicio:
            raise ValueError("O fim da faixa precisa ser depois do início.")
        return v


class PosicaoSchema(Schema):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
