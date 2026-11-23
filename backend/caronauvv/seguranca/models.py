from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.auth.models import ContatoConfianca, Usuario
    from caronauvv.caronas.models import Carona


# Valores possiveis (guardados como texto)
TIPOS_ALERTA = ("parada_longa", "sinal_perdido", "desvio_rota", "pin_sem_gps", "botao_panico")
RESPOSTAS_ALERTA = ("tudo_bem", "preciso_ajuda", "sem_resposta")
STATUS_ALERTA = ("aguardando", "em_revisao", "resolvido")
STATUS_DENUNCIA = ("aberta", "em_analise", "encerrada")


# === Alerta (monitor oculto: "Esta tudo bem?") ===  [EXTRA - seguranca]
class Alerta(db.Model):
    __tablename__ = "alertas"
    __table_args__ = (
        CheckConstraint(check_valores("tipo", TIPOS_ALERTA), name="tipo"),
        CheckConstraint(check_valores("resposta", RESPOSTAS_ALERTA), name="resposta"),
        CheckConstraint(check_valores("status", STATUS_ALERTA), name="status"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    carona_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))  # quem foi perguntado
    tipo: Mapped[str] = mapped_column(db.String(30), nullable=False)
    detalhe: Mapped[Optional[str]] = mapped_column(db.String(300))  # "6 min parado a 400 m da rota"
    lat: Mapped[Optional[float]] = mapped_column(db.Float)           # onde o carro estava (mapa do painel)
    lng: Mapped[Optional[float]] = mapped_column(db.Float)
    resposta: Mapped[Optional[str]] = mapped_column(db.String(20))
    respondido_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="aguardando", index=True)
    contatos_avisados_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), index=True)
    resolvido_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

    carona: Mapped["Carona"] = relationship("Carona")
    usuario: Mapped[Optional["Usuario"]] = relationship("Usuario")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "carona_id": self.carona_id,
            "usuario": self.usuario.to_dict() if self.usuario else None,
            "tipo": self.tipo,
            "detalhe": self.detalhe,
            "lat": self.lat,
            "lng": self.lng,
            "resposta": self.resposta,
            "status": self.status,
            "criado_em": self.created_at.isoformat(timespec="minutes"),
            "resolvido_em": self.resolvido_em.isoformat(timespec="minutes") if self.resolvido_em else None,
        }

    def __repr__(self) -> str:
        return f"<Alerta id={self.id} tipo='{self.tipo}' status='{self.status}'>"


# === LinkCompartilhado ("Link da familia" - sem precisar instalar nada) ===  [EXTRA]
class LinkCompartilhado(db.Model):
    __tablename__ = "links_compartilhados"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    carona_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)  # quem compartilhou
    contato_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("contatos_confianca.id", ondelete="SET NULL"))  # enviado pelo monitor
    token: Mapped[str] = mapped_column(db.String(64), nullable=False, unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)  # fim da viagem
    revogado_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    acessos: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    carona: Mapped["Carona"] = relationship("Carona")
    usuario: Mapped["Usuario"] = relationship("Usuario")
    contato: Mapped[Optional["ContatoConfianca"]] = relationship("ContatoConfianca")

    # "A localizacao some quando a viagem termina"
    @property
    def ativo(self) -> bool:
        return self.revogado_em is None and self.expira_em is not None and self.expira_em > datetime.now()

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "carona_id": self.carona_id,
            "expira_em": self.expira_em.isoformat(timespec="minutes"),
            "ativo": self.ativo,
            "acessos": self.acessos,
        }

    def __repr__(self) -> str:
        return f"<LinkCompartilhado id={self.id} carona_id={self.carona_id} expira_em={self.expira_em}>"


# === Denuncia (usuario denuncia outro) ===  [EXTRA - painel admin]
class Denuncia(db.Model):
    __tablename__ = "denuncias"
    __table_args__ = (
        CheckConstraint("denunciante_id <> denunciado_id", name="nao_autodenunciar"),
        CheckConstraint(check_valores("status", STATUS_DENUNCIA), name="status"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    denunciante_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    denunciado_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    carona_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="SET NULL"))
    motivo: Mapped[str] = mapped_column(db.String(60), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(db.Text)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="aberta", index=True)

    # ------------------------------------------------------
    # ANALISE PELO ADMIN
    # ------------------------------------------------------
    analisada_por_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    resolucao: Mapped[Optional[str]] = mapped_column(db.Text)
    encerrada_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    denunciante: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[denunciante_id])
    denunciado: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[denunciado_id])
    analisada_por: Mapped[Optional["Usuario"]] = relationship("Usuario", foreign_keys=[analisada_por_id])
    carona: Mapped[Optional["Carona"]] = relationship("Carona")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "denunciante": self.denunciante.to_dict(),
            "denunciado": {**self.denunciado.to_dict(), "is_active": self.denunciado.is_active},
            "carona_id": self.carona_id,
            "motivo": self.motivo,
            "descricao": self.descricao,
            "status": self.status,
            "resolucao": self.resolucao,
            "criada_em": self.created_at.isoformat(timespec="minutes"),
            "encerrada_em": self.encerrada_em.isoformat(timespec="minutes") if self.encerrada_em else None,
        }

    def __repr__(self) -> str:
        return f"<Denuncia id={self.id} denunciado_id={self.denunciado_id} status='{self.status}'>"
