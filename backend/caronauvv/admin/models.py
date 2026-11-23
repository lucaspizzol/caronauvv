from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caronauvv.caronas.models import SENTIDOS
from caronauvv.ext.db import check_valores, db

if TYPE_CHECKING:
    from caronauvv.auth.models import Usuario


# === Busca (registro para "Buscas sem resultado, por bairro") ===  [EXTRA - painel]
class Busca(db.Model):
    __tablename__ = "buscas"
    __table_args__ = (
        CheckConstraint(check_valores("sentido", SENTIDOS), name="sentido"),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    bairro: Mapped[str] = mapped_column(db.String(100), nullable=False, index=True)
    sentido: Mapped[str] = mapped_column(db.String(10), nullable=False, default="ida")
    data_desejada: Mapped[date] = mapped_column(db.Date, nullable=False)
    hora_inicio: Mapped[Optional[time]] = mapped_column(db.Time)   # faixa "18:00 - 19:00"
    hora_fim: Mapped[Optional[time]] = mapped_column(db.Time)
    qtd_resultados: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), index=True)

    usuario: Mapped[Optional["Usuario"]] = relationship("Usuario")

    def __repr__(self) -> str:
        return f"<Busca id={self.id} bairro='{self.bairro}' resultados={self.qtd_resultados}>"


# === Configuracao ("Regras e precos" do painel) ===  [EXTRA]
class Configuracao(db.Model):
    __tablename__ = "configuracoes"

    # Valores iniciais inseridos pelo comando seed-db: chave -> (valor, descricao)
    PADROES = {
        "custo_km_combustivel": ("0.55", "Custo do combustível por km (R$), base do valor sugerido"),
        "valor_maximo_passageiro": ("5.00", "Teto do valor por passageiro (R$): nunca mais que o custo"),
        "raio_busca_km": ("2", "Distância máxima da rota até o passageiro na busca (km)"),
        "horas_expirar_pedido": ("2", "Pedido sem resposta expira X horas antes da saída"),
        "minutos_responder_pedido": ("30", "O motorista tem X minutos para responder um pedido de vaga"),
        "minutos_prioridade_fila": ("15", "Carona nova: nos primeiros X min só quem estava na fila do Pedir carona pede vaga"),
        "minutos_alerta_parada": ("6", "Carro parado fora da rota por X min dispara 'Está tudo bem?'"),
        "minutos_sem_resposta_alerta": ("3", "Sem resposta ao alerta em X min, avisa os contatos de confiança"),
        "dias_revelar_avaliacao": ("7", "Notas aparecem quando os dois avaliam ou após X dias"),
        "dias_guardar_gps": ("30", "Trilhas GPS são apagadas após X dias"),
        "preco_gasolina": ("6.29", "Preço do litro da gasolina (R$), usado também por carros flex e híbridos"),
        "preco_etanol": ("4.39", "Preço do litro do etanol (R$)"),
        "preco_diesel": ("6.19", "Preço do litro do diesel (R$)"),
        "preco_kwh": ("0.89", "Preço do kWh para carro elétrico (R$)"),
        "transito_pico_percentual": ("25", "Trânsito: % a mais de consumo no horário de pico (dia útil, 6h30-8h30 e 17h-19h30)"),
        "transito_trecho_percentual": ("10", "Trânsito: % a mais por trecho crítico no pico (pontes, Rod. do Sol, BR-101)"),
        "transito_maximo_percentual": ("50", "Trânsito: acréscimo máximo no consumo (%)"),
        "nota_alerta_avaliacao": ("4", "Avaliação com nota abaixo deste valor gera alerta para a administração"),
        "media_minima_usuario": ("3", "Quem fica com média abaixo deste valor é excluído automaticamente do aplicativo"),
        "avaliacoes_minimas_exclusao": ("1", "Avaliações recebidas necessárias antes de aplicar a exclusão automática"),
        "exigir_cnh_motorista": ("0", "1 = só oferece carona quem tem a CNH verificada; 0 = não exige"),
        "exigir_identidade_passageiro": ("0", "1 = só pede vaga quem tem a identidade verificada; 0 = não exige"),
    }

    chave: Mapped[str] = mapped_column(db.String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(db.String(255), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(db.String(255))
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now(), onupdate=datetime.now)

    # ======================================================
    # LEITURA (cai no padrao se a chave nao estiver no banco)
    # ======================================================
    @classmethod
    def obter(cls, chave: str, padrao: Optional[str] = None) -> Optional[str]:
        config = db.session.get(cls, chave)
        if config is not None:
            return config.valor
        if chave in cls.PADROES:
            return cls.PADROES[chave][0]
        return padrao

    @classmethod
    def obter_int(cls, chave: str, padrao: int) -> int:
        return int(float(cls.obter(chave, str(padrao))))  # "2.5" no painel vira 2, sem erro 500

    @classmethod
    def obter_decimal(cls, chave: str, padrao: str) -> Decimal:
        return Decimal(cls.obter(chave, padrao))

    def __repr__(self) -> str:
        return f"<Configuracao {self.chave}='{self.valor}'>"
