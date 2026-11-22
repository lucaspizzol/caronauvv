from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.auth.models import Usuario, Veiculo
    from caronauvv.avaliacoes.models import Avaliacao, Pagamento


# Valores possiveis (guardados como texto, igual ao status/priority do TaskFlow)
SENTIDOS = ("ida", "volta")                     # Casa -> UVV / UVV -> Casa
STATUS_CARONA = ("ativa", "lotada", "em_andamento", "concluida", "cancelada")
STATUS_SOLICITACAO = ("pendente", "aceita", "recusada", "cancelada", "expirada")
METODOS_EMBARQUE = ("pin", "pin+gps", "gps", "manual")  # "pin": o motorista digitou o PIN do passageiro


# === Carona (oferta do motorista) ===  [MVP]
class Carona(db.Model):
    __tablename__ = "caronas"
    __table_args__ = (
        CheckConstraint("vagas BETWEEN 1 AND 6", name="vagas"),
        CheckConstraint("valor_por_passageiro >= 0", name="valor"),
        CheckConstraint(check_valores("sentido", SENTIDOS), name="sentido"),
        CheckConstraint(check_valores("status", STATUS_CARONA), name="status"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    motorista_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    veiculo_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("veiculos.id", ondelete="SET NULL"))  # [EXTRA]

    # ------------------------------------------------------
    # TRAJETO
    # ------------------------------------------------------
    sentido: Mapped[str] = mapped_column(db.String(10), nullable=False, default="ida")
    bairro_origem: Mapped[str] = mapped_column(db.String(100), nullable=False, index=True)
    endereco_origem: Mapped[str] = mapped_column(db.String(255), nullable=False)
    destino: Mapped[str] = mapped_column(db.String(255), nullable=False, default="UVV - Entrada principal")
    origem_lat: Mapped[Optional[float]] = mapped_column(db.Float)   # [EXTRA] mapa / proximidade
    origem_lng: Mapped[Optional[float]] = mapped_column(db.Float)
    destino_lat: Mapped[Optional[float]] = mapped_column(db.Float)  # [EXTRA] no sentido "volta" o destino e a casa
    destino_lng: Mapped[Optional[float]] = mapped_column(db.Float)
    distancia_km: Mapped[Optional[float]] = mapped_column(db.Float)
    duracao_min: Mapped[Optional[int]] = mapped_column(db.Integer)
    rota_polyline: Mapped[Optional[str]] = mapped_column(db.Text)   # [EXTRA] desenho da rota

    # ------------------------------------------------------
    # HORARIO, VAGAS E VALOR
    # ------------------------------------------------------
    data_hora_saida: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, index=True)
    vagas: Mapped[int] = mapped_column(db.Integer, nullable=False)
    valor_por_passageiro: Mapped[Decimal] = mapped_column(db.Numeric(6, 2), nullable=False, default=0)
    reserva_automatica: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)  # [EXTRA]
    observacoes: Mapped[Optional[str]] = mapped_column(db.String(300))  # "Saio pontualmente; cabe mochila"

    # ------------------------------------------------------
    # STATUS / AUDITORIA
    # ------------------------------------------------------
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="ativa", index=True)
    iniciada_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    concluida_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    cancelada_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), onupdate=datetime.now)

    # ------------------------------------------------------
    # RELACIONAMENTOS
    # ------------------------------------------------------
    motorista: Mapped["Usuario"] = relationship("Usuario", back_populates="caronas_oferecidas", foreign_keys=[motorista_id])
    veiculo: Mapped[Optional["Veiculo"]] = relationship("Veiculo")
    solicitacoes: Mapped[List["Solicitacao"]] = relationship(
        "Solicitacao", back_populates="carona", cascade="all, delete-orphan"
    )
    posicoes: Mapped[List["PosicaoGps"]] = relationship(
        "PosicaoGps", back_populates="carona", cascade="all, delete-orphan"
    )

    # ======================================================
    # REGRA DE NEGOCIO: vagas restantes = vagas - aceitas
    # ======================================================
    @property
    def vagas_restantes(self) -> int:
        aceitas = sum(1 for s in self.solicitacoes if s.status == "aceita")
        return self.vagas - aceitas

    # ======================================================
    # REGRA DE NEGOCIO: telefone e placa so aparecem para o
    # motorista e para passageiros com solicitacao aceita
    # ======================================================
    def pode_ver_contato(self, usuario: Optional["Usuario"]) -> bool:
        if usuario is None:
            return False
        if usuario.id == self.motorista_id:
            return True
        return any(s.passageiro_id == usuario.id and s.status == "aceita" for s in self.solicitacoes)

    def to_dict(self, usuario: Optional["Usuario"] = None) -> dict:
        from caronauvv.avaliacoes.services import reputacao

        def iso(valor: Optional[datetime]) -> Optional[str]:
            return valor.isoformat(timespec="minutes") if valor else None

        ver_contato = self.pode_ver_contato(usuario)
        motorista = self.motorista.to_dict(privado=ver_contato)
        motorista["reputacao"] = reputacao(self.motorista)
        return {
            "id": self.id,
            "sentido": self.sentido,
            "bairro_origem": self.bairro_origem,
            "endereco_origem": self.endereco_origem,
            "destino": self.destino,
            "origem_lat": self.origem_lat,
            "origem_lng": self.origem_lng,
            "distancia_km": self.distancia_km,
            "duracao_min": self.duracao_min,
            "data_hora_saida": self.data_hora_saida.isoformat(timespec="minutes"),
            "vagas": self.vagas,
            "vagas_restantes": self.vagas_restantes,
            "valor_por_passageiro": float(self.valor_por_passageiro),
            "reserva_automatica": self.reserva_automatica,
            "observacoes": self.observacoes,
            "status": self.status,
            "iniciada_em": iso(self.iniciada_em),
            "concluida_em": iso(self.concluida_em),
            "motorista": motorista,
            "veiculo": self.veiculo.to_dict(com_placa=ver_contato) if self.veiculo else None,
        }

    def __repr__(self) -> str:
        return (
            f"<Carona id={self.id} {self.bairro_origem}->{self.destino} "
            f"saida={self.data_hora_saida} status='{self.status}'>"
        )


# === Solicitacao (pedido de vaga do passageiro) ===  [MVP]
class Solicitacao(db.Model):
    __tablename__ = "solicitacoes"
    __table_args__ = (
        # Regra: o passageiro nao pode pedir a mesma carona duas vezes
        UniqueConstraint("carona_id", "passageiro_id", name="uq_solicitacao_carona_passageiro"),
        CheckConstraint(check_valores("status", STATUS_SOLICITACAO), name="status"),
        CheckConstraint(check_valores("metodo_embarque", METODOS_EMBARQUE), name="metodo_embarque"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    carona_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="CASCADE"), nullable=False, index=True)
    passageiro_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)

    # ------------------------------------------------------
    # PONTO DE EMBARQUE
    # ------------------------------------------------------
    endereco_embarque: Mapped[Optional[str]] = mapped_column(db.String(255))
    embarque_lat: Mapped[Optional[float]] = mapped_column(db.Float)   # [EXTRA]
    embarque_lng: Mapped[Optional[float]] = mapped_column(db.Float)
    desvio_min: Mapped[Optional[int]] = mapped_column(db.Integer)      # [EXTRA] "desvio de +1 min"
    distancia_rota_m: Mapped[Optional[int]] = mapped_column(db.Integer)  # [EXTRA] "30 m da rota"
    mensagem: Mapped[Optional[str]] = mapped_column(db.String(300))

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="pendente", index=True)
    respondida_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    expira_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)   # [EXTRA] expira 2h antes da saida

    # ------------------------------------------------------
    # EMBARQUE COM PIN  [EXTRA]
    # ------------------------------------------------------
    pin_embarque: Mapped[Optional[str]] = mapped_column(db.String(4))
    embarcou_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    metodo_embarque: Mapped[Optional[str]] = mapped_column(db.String(20))  # "pin+gps", "gps", "manual"
    faltou: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)  # [EXTRA] "faltas" na tela 6

    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), onupdate=datetime.now)

    # ------------------------------------------------------
    # RELACIONAMENTOS
    # ------------------------------------------------------
    carona: Mapped["Carona"] = relationship("Carona", back_populates="solicitacoes")
    passageiro: Mapped["Usuario"] = relationship("Usuario", back_populates="solicitacoes", foreign_keys=[passageiro_id])
    pagamento: Mapped[Optional["Pagamento"]] = relationship(
        "Pagamento", back_populates="solicitacao", uselist=False, cascade="all, delete-orphan"
    )
    avaliacoes: Mapped[List["Avaliacao"]] = relationship(
        "Avaliacao", back_populates="solicitacao", cascade="all, delete-orphan"
    )

    # ======================================================
    # JSON da API
    # Telefone do passageiro so aparece para o motorista apos o aceite;
    # o PIN de embarque so aparece para o proprio passageiro.
    # ======================================================
    def to_dict(self, usuario: Optional["Usuario"] = None) -> dict:
        def iso(valor: Optional[datetime]) -> Optional[str]:
            return valor.isoformat(timespec="minutes") if valor else None

        dados = {
            "id": self.id,
            "carona_id": self.carona_id,
            "status": self.status,
            "endereco_embarque": self.endereco_embarque,
            "mensagem": self.mensagem,
            "desvio_min": self.desvio_min,
            "criada_em": iso(self.created_at),
            "respondida_em": iso(self.respondida_em),
            "expira_em": iso(self.expira_em),
            "passageiro": self.passageiro.to_dict(privado=self.status == "aceita"),
            "embarcou_em": iso(self.embarcou_em),
            "faltou": self.faltou,
            "pagamento": self.pagamento.to_dict() if self.pagamento else None,
        }
        from caronauvv.avaliacoes.services import reputacao
        dados["passageiro"]["reputacao"] = reputacao(self.passageiro)
        if usuario is not None:
            dados["ja_avaliei"] = any(a.avaliador_id == usuario.id for a in self.avaliacoes)
            if usuario.id == self.passageiro_id:
                dados["pin_embarque"] = self.pin_embarque
        return dados

    def __repr__(self) -> str:
        return (
            f"<Solicitacao id={self.id} carona_id={self.carona_id} "
            f"passageiro_id={self.passageiro_id} status='{self.status}'>"
        )


# === PosicaoGps (trilha da viagem ao vivo) ===  [EXTRA - apagar apos 30 dias]
class PosicaoGps(db.Model):
    __tablename__ = "posicoes_gps"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    carona_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("caronas.id", ondelete="CASCADE"), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(db.Float, nullable=False)
    lng: Mapped[float] = mapped_column(db.Float, nullable=False)
    registrada_em: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), index=True)

    carona: Mapped["Carona"] = relationship("Carona", back_populates="posicoes")

    def __repr__(self) -> str:
        return f"<PosicaoGps carona_id={self.carona_id} ({self.lat}, {self.lng})>"
