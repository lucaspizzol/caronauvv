from pydantic import Field, field_validator

from caronauvv.validacao import Schema, TextoOpcional

from .models import TAGS_MOTORISTA, TAGS_PASSAGEIRO


class AvaliacaoSchema(Schema):
    nota: int = Field(ge=1, le=5)
    comentario: TextoOpcional = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("tags")
    @classmethod
    def _tags_conhecidas(cls, v: list[str]) -> list[str]:
        permitidas = set(TAGS_MOTORISTA) | set(TAGS_PASSAGEIRO)
        desconhecidas = [t for t in v if t not in permitidas]
        if desconhecidas:
            raise ValueError(f"Tag desconhecida: {', '.join(desconhecidas)}.")
        return list(dict.fromkeys(v))  # remove repetidas mantendo a ordem
