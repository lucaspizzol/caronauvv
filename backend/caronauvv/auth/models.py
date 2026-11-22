from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.caronas.models import Carona, Solicitacao


# Preferencias de viagem (inspiradas no "Bla / BlaBla / BlaBlaBla" do BlaBlaCar)
NIVEIS_CONVERSA = ("quieto", "depende", "conversador")


# === Usuario (aluno: pode ser motorista e passageiro) ===  [MVP]
class Usuario(db.Model):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(check_valores("pref_conversa", NIVEIS_CONVERSA), name="pref_conversa"),
    )

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
    bio: Mapped[Optional[str]] = mapped_column(db.String(300))  # "Curto rock e saio pontualmente"

    # ======================================================
    # PREFERENCIAS DE VIAGEM (aparecem no perfil publico)
    # ======================================================
    pref_conversa: Mapped[str] = mapped_column(db.String(15), nullable=False, default="depende", server_default="depende")
    pref_musica: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True, server_default=db.true())
    pref_animais: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, server_default=db.false())
    pref_fumar: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, server_default=db.false())

    # ======================================================
    # CONFIANCA: e-mail institucional verificado por codigo
    # e perfil verificado pelo admin (carteirinha da UVV)
    # ======================================================
    email_verificado: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, server_default=db.false())
    codigo_verificacao_hash: Mapped[Optional[str]] = mapped_column(db.String(255))
    codigo_expira_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    codigo_tentativas: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0, server_default="0")
    verificacao_solicitada_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

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
        from flask import current_app, has_app_context
        from werkzeug.security import generate_password_hash
        # Producao: scrypt (padrao do Werkzeug). Nos testes, um metodo mais leve deixa a suite rapida.
        metodo = current_app.config.get("PASSWORD_HASH_METHOD", "scrypt") if has_app_context() else "scrypt"
        self.senha_hash = generate_password_hash(senha, method=metodo)

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
            "email_verificado": self.email_verificado,
            "bio": self.bio,
            "preferencias": self.preferencias(),
            "membro_desde": self.created_at.date().isoformat() if self.created_at else None,
        }
        if privado:
            dados.update({
                "matricula": self.matricula,
                "email": self.email,
                "telefone": self.telefone,
                "endereco": self.endereco,
                "chave_pix": self.chave_pix,
                "is_admin": self.is_admin,
                "verificacao_solicitada_em": (
                    self.verificacao_solicitada_em.isoformat(timespec="minutes")
                    if self.verificacao_solicitada_em else None
                ),
            })
        return dados

    def preferencias(self) -> dict:
        return {
            "conversa": self.pref_conversa,
            "musica": self.pref_musica,
            "animais": self.pref_animais,
            "fumar": self.pref_fumar,
        }

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

    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "telefone": self.telefone}

    def __repr__(self) -> str:
        return f"<ContatoConfianca id={self.id} nome='{self.nome}'>"
