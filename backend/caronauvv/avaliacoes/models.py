from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.auth.models import Usuario
    from caronauvv.caronas.models import Solicitacao


# Valores possiveis (guardados como texto)
TAGS_SUGERIDAS = ("Pontual", "Dirige bem", "Carro limpo", "Boa conversa")  # tela 11 (texto livre no banco)
METODOS_PAGAMENTO = ("pix", "dinheiro")
STATUS_PAGAMENTO = ("pendente", "pago", "cancelado")


# === Avaliacao (nota de 1 a 5 depois da carona) ===  [EXTRA - recomendado]
# Regra da tela 11: as notas so aparecem quando os dois avaliam ou apos 7 dias.
class Avaliacao(db.Model):
    __tablename__ = "avaliacoes"
    __table_args__ = (
        CheckConstraint("nota BETWEEN 1 AND 5", name="nota"),
        CheckConstraint("avaliador_id <> avaliado_id", name="nao_autoavaliar"),
        # cada pessoa avalia a outra uma unica vez por viagem
        UniqueConstraint("solicitacao_id", "avaliador_id", name="uq_avaliacao_solicitacao_avaliador"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    solicitacao_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("solicitacoes.id", ondelete="CASCADE"), nullable=False, index=True)
    avaliador_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    avaliado_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    nota: Mapped[int] = mapped_column(db.Integer, nullable=False)
    comentario: Mapped[Optional[str]] = mapped_column(db.String(500))
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    solicitacao: Mapped["Solicitacao"] = relationship("Solicitacao", back_populates="avaliacoes")
    avaliador: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[avaliador_id])
    avaliado: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[avaliado_id])
    tags: Mapped[List["AvaliacaoTag"]] = relationship(
        "AvaliacaoTag", back_populates="avaliacao", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Avaliacao id={self.id} avaliado_id={self.avaliado_id} nota={self.nota}>"


# === AvaliacaoTag ("Pontual", "Dirige bem", "Carro limpo", "Boa conversa") ===  [EXTRA]
class AvaliacaoTag(db.Model):
    __tablename__ = "avaliacao_tags"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "tag", name="uq_avaliacao_tag"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(db.String(40), nullable=False)

    avaliacao: Mapped["Avaliacao"] = relationship("Avaliacao", back_populates="tags")

    def __repr__(self) -> str:
        return f"<AvaliacaoTag avaliacao_id={self.avaliacao_id} tag='{self.tag}'>"


# === Pagamento (rateio por Pix, direto para o motorista) ===  [EXTRA]
class Pagamento(db.Model):
    __tablename__ = "pagamentos"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="valor"),
        CheckConstraint(check_valores("metodo", METODOS_PAGAMENTO), name="metodo"),
        CheckConstraint(check_valores("status", STATUS_PAGAMENTO), name="status"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    solicitacao_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("solicitacoes.id", ondelete="CASCADE"), nullable=False, unique=True)
    valor: Mapped[Decimal] = mapped_column(db.Numeric(6, 2), nullable=False)
    metodo: Mapped[str] = mapped_column(db.String(20), nullable=False, default="pix")
    pix_copia_cola: Mapped[Optional[str]] = mapped_column(db.Text)  # codigo do QR / botao "Copiar Pix"
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="pendente")
    pago_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), onupdate=datetime.now)

    solicitacao: Mapped["Solicitacao"] = relationship("Solicitacao", back_populates="pagamento")

    def __repr__(self) -> str:
        return f"<Pagamento id={self.id} valor={self.valor} status='{self.status}'>"
