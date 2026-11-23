from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import db

if TYPE_CHECKING:
    from caronauvv.auth.models import Usuario
    from caronauvv.caronas.models import Carona


# Tipos usados hoje (texto livre no banco, para nao exigir migracao a cada tipo novo)
TIPOS_NOTIFICACAO = (
    "novo_pedido", "vaga_confirmada", "vaga_recusada", "pedido_expirado", "pedido_cancelado",
    "viagem_iniciada", "embarque_confirmado", "pagamento_informado", "nova_avaliacao",
    "lembrete_saida", "motorista_chegando", "carona_cancelada",
    "avaliacao_pendente", "alerta_seguranca", "perfil_verificado",
    "seguranca_conta",   # senha alterada, autenticador ligado/desligado, foto removida pela administracao
    "desembarque",       # motorista ou passageiro registrou a saida do carro
    "carona_da_fila",    # apareceu carona compativel com o "Pedir carona" do aluno
    "documento",         # identidade/CNH enviada (para o admin), aprovada ou recusada (para o aluno)
    "avaliacao_baixa",   # para o admin: alguem recebeu nota abaixo do limite
    "exclusao_automatica",  # para o admin: alguem saiu do app por media baixa
)


# === Notificacao ("Vaga confirmada", "Sua carona sai em 15 min") ===  [EXTRA - recomendado]
class Notificacao(db.Model):
    __tablename__ = "notificacoes"
    __table_args__ = (
        # "minhas notificacoes nao lidas" e a consulta mais comum
        db.Index("ix_notificacoes_usuario_lida", "usuario_id", "lida"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    carona_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="SET NULL"))
    tipo: Mapped[str] = mapped_column(db.String(40), nullable=False)
    titulo: Mapped[str] = mapped_column(db.String(120), nullable=False)
    texto: Mapped[str] = mapped_column(db.String(500), nullable=False)
    lida: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), index=True)

    usuario: Mapped["Usuario"] = relationship("Usuario")
    carona: Mapped[Optional["Carona"]] = relationship("Carona")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "texto": self.texto,
            "carona_id": self.carona_id,
            "lida": self.lida,
            "criada_em": self.created_at.isoformat(timespec="minutes"),
        }

    def __repr__(self) -> str:
        return f"<Notificacao id={self.id} tipo='{self.tipo}' lida={self.lida}>"
