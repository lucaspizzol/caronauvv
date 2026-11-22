from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import db

if TYPE_CHECKING:
    from caronauvv.caronas.models import Carona, Solicitacao


# === Usuario (aluno: pode ser motorista e passageiro) ===  [MVP]
class Usuario(db.Model):
    __tablename__ = "usuarios"

    # ======================================================
    # IDENTIFICACAO
    # ======================================================
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    matricula: Mapped[str] = mapped_column(db.String(20), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True, index=True)

    # ======================================================
    # PERFIL
    # ======================================================
    nome: Mapped[str] = mapped_column(db.String(150), nullable=False)
    curso: Mapped[Optional[str]] = mapped_column(db.String(120))
    telefone: Mapped[str] = mapped_column(db.String(20), nullable=False)
    bairro: Mapped[str] = mapped_column(db.String(100), nullable=False, index=True)
    endereco: Mapped[Optional[str]] = mapped_column(db.String(255))   # [EXTRA] tela Inicio: "Rua Itaunas, 120"
    casa_lat: Mapped[Optional[float]] = mapped_column(db.Float)        # [EXTRA] busca por proximidade da rota
    casa_lng: Mapped[Optional[float]] = mapped_column(db.Float)
    foto_url: Mapped[Optional[str]] = mapped_column(db.String(500))
    chave_pix: Mapped[Optional[str]] = mapped_column(db.String(150))  # [EXTRA] Pix do rateio

    # ======================================================
    # SENHA LOCAL
    # ======================================================
    senha_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)

    # ======================================================
    # AUDITORIA / PERMISSOES
    # ======================================================
    is_admin: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)  # [EXTRA] painel
    verificado: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    ultimo_login_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)  # [EXTRA] KPI "usuarios que voltaram"
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), onupdate=datetime.now)

    # ------------------------------------------------------
    # RELACIONAMENTOS
    # ------------------------------------------------------
    veiculos: Mapped[List["Veiculo"]] = relationship(
        "Veiculo", back_populates="dono", cascade="all, delete-orphan"
    )
    caronas_oferecidas: Mapped[List["Carona"]] = relationship(
        "Carona", back_populates="motorista", foreign_keys="Carona.motorista_id"
    )
    solicitacoes: Mapped[List["Solicitacao"]] = relationship(
        "Solicitacao", back_populates="passageiro", foreign_keys="Solicitacao.passageiro_id"
    )
    contatos_confianca: Mapped[List["ContatoConfianca"]] = relationship(
        "ContatoConfianca", back_populates="usuario", cascade="all, delete-orphan"
    )

    # ======================================================
    # SENHA (hash com Werkzeug, que ja vem com o Flask)
    # ======================================================
    def set_senha(self, senha: str) -> None:
        from werkzeug.security import generate_password_hash
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.senha_hash, senha)

    # ======================================================
    # JSON da API
    # privado=False: o que qualquer aluno pode ver (sem telefone/e-mail/Pix).
    # privado=True: o proprio usuario, ou motorista/passageiro com solicitacao aceita.
    # ======================================================
    def to_dict(self, privado: bool = False) -> dict:
        dados = {
            "id": self.id,
            "nome": self.nome,
            "curso": self.curso,
            "bairro": self.bairro,
            "foto_url": self.foto_url,
            "verificado": self.verificado,
        }
        if privado:
            dados.update({
                "matricula": self.matricula,
                "email": self.email,
                "telefone": self.telefone,
                "endereco": self.endereco,
                "chave_pix": self.chave_pix,
                "is_admin": self.is_admin,
            })
        return dados

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} matricula='{self.matricula}' nome='{self.nome}'>"


# === Veiculo (carro do motorista) ===  [EXTRA - recomendado]
class Veiculo(db.Model):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    modelo: Mapped[str] = mapped_column(db.String(80), nullable=False)       # ex.: HB20
    cor: Mapped[str] = mapped_column(db.String(30), nullable=False)          # ex.: Branco
    placa: Mapped[str] = mapped_column(db.String(10), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    dono: Mapped["Usuario"] = relationship("Usuario", back_populates="veiculos")

    # A placa so aparece depois que a solicitacao e aceita
    def to_dict(self, com_placa: bool = False) -> dict:
        dados = {"id": self.id, "modelo": self.modelo, "cor": self.cor}
        if com_placa:
            dados["placa"] = self.placa
        return dados

    def __repr__(self) -> str:
        return f"<Veiculo id={self.id} modelo='{self.modelo}' placa='{self.placa}'>"


# === ContatoConfianca ("Mae", "Julia" - recebem o link da viagem) ===  [EXTRA - seguranca]
class ContatoConfianca(db.Model):
    __tablename__ = "contatos_confianca"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    telefone: Mapped[str] = mapped_column(db.String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="contatos_confianca")

    def __repr__(self) -> str:
        return f"<ContatoConfianca id={self.id} nome='{self.nome}'>"
