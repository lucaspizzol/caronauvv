from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.caronas.models import Carona, Solicitacao


# Preferencias de viagem (inspiradas no "Bla / BlaBla / BlaBlaBla" do BlaBlaCar)
NIVEIS_CONVERSA = ("quieto", "depende", "conversador")

# Tipo de energia do carro: define o preco usado no calculo do rateio (caronas/combustivel.py)
ENERGIAS = ("gasolina", "etanol", "flex", "diesel", "hibrido", "eletrico")

# Documentos que o aluno envia para ganhar os selos de confianca
TIPOS_DOCUMENTO = ("identidade", "cnh")
STATUS_DOCUMENTO = ("pendente", "aprovado", "recusado")


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
    # Endereco da foto de perfil (/api/fotos/<token>). O arquivo fica na tabela fotos_perfil.
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
    # Sobe a cada troca de senha: os tokens de login antigos deixam de valer
    sessao_versao: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0, server_default="0")

    # ======================================================
    # RECUPERACAO DE SENHA ("esqueci minha senha"): codigo de 6 numeros
    # enviado por e-mail, guardado so como HMAC (igual ao da verificacao)
    # ======================================================
    reset_codigo_hash: Mapped[Optional[str]] = mapped_column(db.String(255))
    reset_expira_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    reset_tentativas: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0, server_default="0")
    reset_enviado_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

    # ======================================================
    # VERIFICACAO EM DUAS ETAPAS (aplicativo autenticador, TOTP)
    # totp_ultimo_passo: cada codigo so vale uma vez (ver auth/totp.py)
    # ======================================================
    totp_segredo: Mapped[Optional[str]] = mapped_column(db.String(64))
    totp_ativo: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False, server_default=db.false())
    totp_ativado_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    totp_ultimo_passo: Mapped[Optional[int]] = mapped_column(db.BigInteger)
    totp_falhas: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0, server_default="0")
    totp_bloqueado_ate: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

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
    foto: Mapped[Optional["FotoPerfil"]] = relationship(
        "FotoPerfil", back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )
    codigos_reserva: Mapped[List["CodigoReserva"]] = relationship(
        "CodigoReserva", back_populates="usuario", cascade="all, delete-orphan"
    )
    documentos: Mapped[List["Documento"]] = relationship(
        "Documento", back_populates="usuario", cascade="all, delete-orphan",
        foreign_keys="Documento.usuario_id",
    )

    # ======================================================
    # SELOS DE DOCUMENTO (identidade e CNH conferidas pela administracao)
    # ======================================================
    def documento(self, tipo: str) -> Optional["Documento"]:
        return next((d for d in self.documentos if d.tipo == tipo), None)

    def documento_aprovado(self, tipo: str) -> bool:
        doc = self.documento(tipo)
        if doc is None or doc.status != "aprovado":
            return False
        # CNH vencida deixa de valer, mesmo aprovada
        return doc.validade is None or doc.validade >= date.today()

    @property
    def identidade_verificada(self) -> bool:
        return self.documento_aprovado("identidade")

    @property
    def cnh_verificada(self) -> bool:
        return self.documento_aprovado("cnh")

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
            "identidade_verificada": self.identidade_verificada,
            "cnh_verificada": self.cnh_verificada,
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
                "dois_fatores": self.totp_ativo,
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
    __table_args__ = (
        CheckConstraint(check_valores("energia", ENERGIAS), name="energia"),
        CheckConstraint("consumo_km IS NULL OR (consumo_km > 0 AND consumo_km <= 60)", name="consumo"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    modelo: Mapped[str] = mapped_column(db.String(80), nullable=False)       # ex.: HB20
    # Energia e consumo: base do calculo do combustivel (km por litro; no eletrico, km por kWh)
    energia: Mapped[str] = mapped_column(db.String(15), nullable=False, default="flex", server_default="flex")
    consumo_km: Mapped[Optional[float]] = mapped_column(db.Float)
    cor: Mapped[str] = mapped_column(db.String(30), nullable=False)          # ex.: Branco
    placa: Mapped[str] = mapped_column(db.String(10), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    dono: Mapped["Usuario"] = relationship("Usuario", back_populates="veiculos")

    # A placa so aparece depois que a solicitacao e aceita
    def to_dict(self, com_placa: bool = False) -> dict:
        dados = {"id": self.id, "modelo": self.modelo, "cor": self.cor,
                 "energia": self.energia, "consumo_km": self.consumo_km}
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


# === FotoPerfil (arquivo da foto de perfil) ===  [EXTRA - confianca]
# Fica no banco, e nao numa pasta, porque na hospedagem serverless (Vercel) o disco
# e apagado a cada execucao. Tabela separada: listar usuarios nao carrega a imagem.
class FotoPerfil(db.Model):
    __tablename__ = "fotos_perfil"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True)
    # Endereco aleatorio: so recebe o link quem esta logado, e ele muda a cada foto nova
    token: Mapped[str] = mapped_column(db.String(32), nullable=False, unique=True, index=True)
    mime: Mapped[str] = mapped_column(db.String(20), nullable=False)   # image/jpeg, image/png ou image/webp
    tamanho: Mapped[int] = mapped_column(db.Integer, nullable=False)    # bytes
    dados: Mapped[bytes] = mapped_column(db.LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="foto")

    def __repr__(self) -> str:
        return f"<FotoPerfil usuario_id={self.usuario_id} mime='{self.mime}' tamanho={self.tamanho}>"


# === CodigoReserva (entra no lugar do autenticador se o aluno perder o celular) ===  [EXTRA - seguranca]
class CodigoReserva(db.Model):
    __tablename__ = "codigos_reserva"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo_hash: Mapped[str] = mapped_column(db.String(64), nullable=False)  # HMAC-SHA256, nunca o codigo em texto
    usado_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)         # cada codigo vale uma vez
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="codigos_reserva")

    def __repr__(self) -> str:
        return f"<CodigoReserva id={self.id} usuario_id={self.usuario_id} usado={self.usado_em is not None}>"


# === Documento (identidade ou CNH enviada para verificacao) ===  [EXTRA - confianca]
# A imagem so existe enquanto a administracao nao analisa: depois de aprovar ou
# recusar, ela e apagada e fica so o resultado (minimizacao de dados, LGPD).
class Documento(db.Model):
    __tablename__ = "documentos"
    __table_args__ = (
        UniqueConstraint("usuario_id", "tipo", name="uq_documentos_usuario_tipo"),
        CheckConstraint(check_valores("tipo", TIPOS_DOCUMENTO), name="tipo"),
        CheckConstraint(check_valores("status", STATUS_DOCUMENTO), name="status"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(db.String(20), nullable=False)
    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default="pendente", index=True)
    validade: Mapped[Optional[date]] = mapped_column(db.Date)          # CNH: vale ate esta data
    mime: Mapped[Optional[str]] = mapped_column(db.String(20))
    tamanho: Mapped[Optional[int]] = mapped_column(db.Integer)
    dados: Mapped[Optional[bytes]] = mapped_column(db.LargeBinary)     # apagado depois da analise
    motivo_recusa: Mapped[Optional[str]] = mapped_column(db.String(255))
    enviado_em: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())
    analisado_em: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    analisado_por_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="documentos", foreign_keys=[usuario_id])
    analisado_por: Mapped[Optional["Usuario"]] = relationship("Usuario", foreign_keys=[analisado_por_id])

    @property
    def vencido(self) -> bool:
        return self.validade is not None and self.validade < date.today()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "status": self.status,
            "validade": self.validade.isoformat() if self.validade else None,
            "vencido": self.vencido,
            "tem_imagem": self.dados is not None,
            "motivo_recusa": self.motivo_recusa,
            "enviado_em": self.enviado_em.isoformat(timespec="minutes") if self.enviado_em else None,
            "analisado_em": self.analisado_em.isoformat(timespec="minutes") if self.analisado_em else None,
        }

    def __repr__(self) -> str:
        return f"<Documento id={self.id} usuario_id={self.usuario_id} tipo='{self.tipo}' status='{self.status}'>"
