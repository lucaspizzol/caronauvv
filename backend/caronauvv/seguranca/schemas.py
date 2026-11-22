from typing import Literal

from pydantic import Field

from caronauvv.validacao import Schema, TextoOpcional

MOTIVOS_DENUNCIA = (
    "nao_compareceu", "direcao_perigosa", "comportamento_inadequado",
    "assedio", "cobranca_indevida", "perfil_falso", "outro",
)


class DenunciaSchema(Schema):
    denunciado_id: int
    carona_id: int | None = None
    motivo: Literal[MOTIVOS_DENUNCIA]  # type: ignore[valid-type]
    descricao: TextoOpcional = Field(default=None, max_length=1000)


class SosSchema(Schema):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    detalhe: TextoOpcional = Field(default=None, max_length=300)
