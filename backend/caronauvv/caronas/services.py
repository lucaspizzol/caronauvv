import secrets
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import selectinload

from caronauvv.admin.models import Busca, Configuracao
from caronauvv.auth.models import Usuario, Veiculo
from caronauvv.auth.services import exigir_email_verificado
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar

from .models import SENTIDOS, Carona, PosicaoGps, Solicitacao
from .schemas import CaronaEdicaoSchema, CaronaNovaSchema, PedidoVagaSchema

STATUS_EDITAVEIS = ("ativa", "lotada")
STATUS_EM_ABERTO = ("ativa", "lotada", "em_andamento")
STATUS_SOLICITACAO_ATIVOS = ("pendente", "aceita")
PRAZO_RESPOSTA = timedelta(hours=2)          # pedido sem resposta expira 2 h antes da saida
JANELA_INICIO = timedelta(minutes=30)        # o motorista pode iniciar a viagem 30 min antes


# ==========================================================
# CONVERSAO DE FILTROS DA BUSCA (query string)
# ==========================================================
def _data(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ApiError("data inválida (use AAAA-MM-DD).")


def _hora(valor: str) -> time:
    try:
        return time.fromisoformat(valor)
    except ValueError:
        raise ApiError("hora inválida (use HH:MM).")


def _aceitas(carona: Carona) -> int:
    return sum(1 for s in carona.solicitacoes if s.status == "aceita")


def _primeiro_nome(usuario: Usuario) -> str:
    return usuario.nome.split()[0]


def _quando(carona: Carona) -> str:
    saida = carona.data_hora_saida
    return f"{saida:%d/%m} às {saida:%H:%M}"


# ==========================================================
# VALOR DO RATEIO (carona solidaria: ninguem lucra)
# ==========================================================
def teto_rateio() -> Decimal:
    return Configuracao.obter_decimal("valor_maximo_passageiro", "5.00")


def valor_sugerido(distancia_km: float, vagas: int) -> Decimal:
    """Custo do combustivel dividido entre motorista e passageiros, limitado ao teto."""
    custo_km = Configuracao.obter_decimal("custo_km_combustivel", "0.55")
    valor = (custo_km * Decimal(str(distancia_km)) / Decimal(vagas + 1)).quantize(Decimal("0.50"))
    return min(max(valor, Decimal("0")), teto_rateio())


def _aplicar_dados(carona: Carona, campos: dict, motorista: Usuario) -> None:
    """Aplica na carona os campos ja validados pelo schema, checando as regras do banco."""
    # Regra: nao e possivel criar carona com data/hora no passado
    if "data_hora_saida" in campos and campos["data_hora_saida"] <= datetime.now():
        raise ApiError("A data/hora de saída precisa ser no futuro.")

    if "vagas" in campos:
        aceitas = _aceitas(carona)
        if campos["vagas"] < aceitas:
            raise ApiError(f"Já há {aceitas} passageiro(s) aceito(s); não dá para ter só {campos['vagas']} vaga(s).")

    if "valor_por_passageiro" in campos:
        valor = campos["valor_por_passageiro"].quantize(Decimal("0.01"))
        teto = teto_rateio()
        if valor > teto:
            teto_br = f"{teto:.2f}".replace(".", ",")
            raise ApiError(
                f"Carona solidária: o rateio máximo é R$ {teto_br} por pessoa (só para dividir o combustível)."
            )
        campos["valor_por_passageiro"] = valor

    if campos.get("veiculo_id") is not None:
        veiculo = db.session.get(Veiculo, campos["veiculo_id"])
        if veiculo is None or veiculo.usuario_id != motorista.id:
            raise ApiError("Veículo não encontrado entre os seus veículos.")

    for campo, valor in campos.items():
        setattr(carona, campo, valor)


# ==========================================================
# REGRA DE NEGOCIO: carona sem vagas fica "lotada" e sai da busca
# (usada tambem pelas solicitacoes ao aceitar/cancelar)
# ==========================================================
def atualizar_lotacao(carona: Carona) -> None:
    if carona.status in STATUS_EDITAVEIS:
        carona.status = "lotada" if carona.vagas_restantes <= 0 else "ativa"


def _exigir_motorista(carona: Carona, usuario: Usuario) -> None:
    if carona.motorista_id != usuario.id:
        raise ApiError("Só o motorista pode alterar esta carona.", 403)


def participa(carona: Carona, usuario: Usuario) -> bool:
    """Motorista ou passageiro com vaga confirmada."""
    return carona.pode_ver_contato(usuario)


# ==========================================================
# CONSULTAS
# ==========================================================
def _consulta_base():
    return db.select(Carona).options(
        selectinload(Carona.solicitacoes),
        selectinload(Carona.motorista),
        selectinload(Carona.veiculo),
    )


def buscar_carona(carona_id: int) -> Carona:
    carona = db.session.scalar(_consulta_base().where(Carona.id == carona_id))
    if carona is None:
        raise ApiError("Carona não encontrada.", 404)
    return carona


def listar_caronas(filtros, usuario: Usuario | None = None) -> list[Carona]:
    """
    Busca de caronas disponiveis: so status "ativa" e com saida no futuro.
    Filtros (query string): bairro, sentido, data (AAAA-MM-DD),
    hora_inicio e hora_fim (HH:MM). Sem data, a faixa de horario vale para hoje.
    Buscas por bairro ficam registradas (tabela buscas) para o painel do admin
    mostrar onde falta oferta de carona.
    """
    consulta = (
        _consulta_base()
        .where(Carona.status == "ativa", Carona.data_hora_saida > datetime.now())
        .order_by(Carona.data_hora_saida)
    )

    bairro = (filtros.get("bairro") or "").strip()
    if bairro:
        consulta = consulta.where(Carona.bairro_origem.ilike(f"%{bairro}%"))

    sentido = filtros.get("sentido")
    if sentido:
        if sentido not in SENTIDOS:
            raise ApiError(f"sentido deve ser um de: {', '.join(SENTIDOS)}.")
        consulta = consulta.where(Carona.sentido == sentido)

    data, hora_inicio, hora_fim = filtros.get("data"), filtros.get("hora_inicio"), filtros.get("hora_fim")
    dia = _data(data) if data else date.today()
    h_ini = _hora(hora_inicio) if hora_inicio else None
    h_fim = _hora(hora_fim) if hora_fim else None
    if data or h_ini or h_fim:
        inicio = datetime.combine(dia, h_ini or time.min)
        fim = datetime.combine(dia, h_fim or time.max)
        consulta = consulta.where(Carona.data_hora_saida.between(inicio, fim))

    # Nao mostra para o aluno as proprias caronas nem as de contas suspensas
    if usuario is not None:
        consulta = consulta.where(Carona.motorista_id != usuario.id)
    consulta = consulta.join(Carona.motorista).where(Usuario.is_active.is_(True))

    caronas = list(db.session.scalars(consulta))

    if bairro:
        db.session.add(Busca(
            usuario_id=usuario.id if usuario else None, bairro=bairro[:100],
            sentido=sentido or "ida", data_desejada=dia, hora_inicio=h_ini, hora_fim=h_fim,
            qtd_resultados=len(caronas),
        ))
        db.session.commit()
    return caronas


def caronas_do_motorista(usuario: Usuario, status: str | None = None) -> list[Carona]:
    """ "Minhas caronas" do motorista: todas as que ele ofereceu, mais recentes primeiro."""
    consulta = (
        _consulta_base()
        .where(Carona.motorista_id == usuario.id)
        .order_by(Carona.data_hora_saida.desc())
    )
    if status:
        consulta = consulta.where(Carona.status == status)
    return list(db.session.scalars(consulta))


# ==========================================================
# CRIAR / EDITAR / CANCELAR
# ==========================================================
def criar_carona(motorista: Usuario, dados: CaronaNovaSchema) -> Carona:
    exigir_email_verificado(motorista, "oferecer carona")
    carona = Carona(motorista_id=motorista.id, status="ativa")
    _aplicar_dados(carona, dados.preenchidos(), motorista)
    db.session.add(carona)
    db.session.commit()
    return carona


def editar_carona(carona: Carona, usuario: Usuario, dados: CaronaEdicaoSchema) -> Carona:
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EDITAVEIS:
        raise ApiError(f"Não é possível editar uma carona {carona.status}.")

    _aplicar_dados(carona, dados.preenchidos(), usuario)
    atualizar_lotacao(carona)
    db.session.commit()
    return carona


def cancelar_carona(carona: Carona, usuario: Usuario) -> Carona:
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EDITAVEIS:
        raise ApiError(f"Não é possível cancelar uma carona {carona.status}.")

    # Regra: cancelar a carona cancela as solicitacoes em aberto (e avisa os passageiros)
    carona.status = "cancelada"
    carona.cancelada_em = datetime.now()
    for solicitacao in carona.solicitacoes:
        if solicitacao.status in STATUS_SOLICITACAO_ATIVOS:
            solicitacao.status = "cancelada"
            solicitacao.pin_embarque = None
            notificar(solicitacao.passageiro, "carona_cancelada", "Carona cancelada",
                      f"{_primeiro_nome(usuario)} cancelou a carona de {_quando(carona)}. "
                      "Busque outra opção em Buscar caronas.", carona)
    db.session.commit()
    return carona


# ==========================================================
# CICLO DA VIAGEM (inspirado no Uber):
# iniciar -> confirmar embarque com o PIN de cada passageiro -> concluir
# ==========================================================
def iniciar_carona(carona: Carona, usuario: Usuario) -> Carona:
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EDITAVEIS:
        raise ApiError(f"Não é possível iniciar uma carona {carona.status}.")
    if datetime.now() < carona.data_hora_saida - JANELA_INICIO:
        raise ApiError("A viagem só pode ser iniciada a partir de 30 minutos antes da saída.")
    aceitos = [s for s in carona.solicitacoes if s.status == "aceita"]
    if not aceitos:
        raise ApiError("Nenhum passageiro confirmado. Cancele a carona se não for mais sair.")

    carona.status = "em_andamento"
    carona.iniciada_em = datetime.now()
    for solicitacao in carona.solicitacoes:
        if solicitacao.status == "pendente":
            solicitacao.status = "expirada"
    for solicitacao in aceitos:
        notificar(solicitacao.passageiro, "viagem_iniciada", f"{_primeiro_nome(usuario)} iniciou a viagem",
                  f"Esteja no ponto de embarque. Mostre seu PIN {solicitacao.pin_embarque} ao motorista.", carona)
    db.session.commit()
    return carona


def _solicitacao_da_viagem(solicitacao: Solicitacao, usuario: Usuario) -> Carona:
    carona = solicitacao.carona
    _exigir_motorista(carona, usuario)
    if carona.status != "em_andamento":
        raise ApiError("Inicie a viagem antes de registrar o embarque.")
    if solicitacao.status != "aceita":
        raise ApiError("Este passageiro não tem vaga confirmada.")
    if solicitacao.embarcou_em is not None:
        raise ApiError("Este passageiro já embarcou.")
    return carona


def confirmar_embarque(solicitacao: Solicitacao, usuario: Usuario, pin: str) -> Solicitacao:
    """O passageiro fala o PIN e o motorista digita: garante que entrou no carro certo."""
    carona = _solicitacao_da_viagem(solicitacao, usuario)
    if not secrets.compare_digest(pin, solicitacao.pin_embarque or ""):
        raise ApiError("PIN incorreto. Confira com o passageiro.")
    solicitacao.embarcou_em = datetime.now()
    solicitacao.metodo_embarque = "pin"
    solicitacao.faltou = False
    notificar(solicitacao.passageiro, "embarque_confirmado", "Embarque confirmado",
              f"Boa viagem! Você está no carro de {_primeiro_nome(carona.motorista)}.", carona)
    db.session.commit()
    return solicitacao


def marcar_falta(solicitacao: Solicitacao, usuario: Usuario) -> Solicitacao:
    """Passageiro confirmado que nao apareceu: conta como falta na reputacao dele."""
    _solicitacao_da_viagem(solicitacao, usuario)
    solicitacao.faltou = True
    db.session.commit()
    return solicitacao


def concluir_carona(carona: Carona, usuario: Usuario) -> Carona:
    """
    Funcionalidade 6 do MVP: depois do horario da viagem, o motorista marca a
    carona como concluida. O historico (passageiros aceitos) e mantido; pedidos
    que ficaram sem resposta passam para "expirada". Motorista e passageiros
    recebem o convite para se avaliarem.
    """
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EM_ABERTO:
        raise ApiError(f"Não é possível concluir uma carona {carona.status}.")
    if carona.status != "em_andamento" and carona.data_hora_saida > datetime.now():
        raise ApiError("A carona só pode ser concluída depois do horário de saída.")

    carona.status = "concluida"
    carona.concluida_em = datetime.now()
    viajaram = 0
    for solicitacao in carona.solicitacoes:
        if solicitacao.status == "pendente":
            solicitacao.status = "expirada"
        elif solicitacao.status == "aceita" and not solicitacao.faltou:
            viajaram += 1
            notificar(solicitacao.passageiro, "avaliacao_pendente", "Como foi a viagem?",
                      f"Avalie {_primeiro_nome(usuario)} e ajude a comunidade a confiar no CaronaUVV.", carona)
    if viajaram:
        notificar(usuario, "avaliacao_pendente", "Avalie seus passageiros",
                  f"Sua carona de {_quando(carona)} foi concluída. Conte como foram os passageiros.", carona)
    db.session.commit()
    return carona


def registrar_posicao(carona: Carona, usuario: Usuario, lat: float, lng: float) -> PosicaoGps:
    """GPS do celular do motorista durante a viagem (aparece no link da familia)."""
    _exigir_motorista(carona, usuario)
    if carona.status != "em_andamento":
        raise ApiError("A localização só é registrada com a viagem em andamento.")
    posicao = PosicaoGps(carona_id=carona.id, lat=lat, lng=lng)
    db.session.add(posicao)
    db.session.commit()
    return posicao


# ==========================================================
# SOLICITACOES (pedido de vaga)
# ==========================================================
def _prazo_resposta(carona: Carona) -> datetime:
    # Se a carona sai em menos de 2 h, o motorista pode responder ate a saida
    limite = carona.data_hora_saida - PRAZO_RESPOSTA
    return limite if limite > datetime.now() else carona.data_hora_saida


def expirar_vencidas(solicitacoes) -> None:
    """Marca como "expirada" os pedidos pendentes que passaram do prazo (o chamador faz o commit)."""
    agora = datetime.now()
    for s in solicitacoes:
        if s.status == "pendente" and s.expira_em is not None and s.expira_em <= agora:
            s.status = "expirada"


def _aceitar(solicitacao: Solicitacao) -> None:
    solicitacao.status = "aceita"
    solicitacao.respondida_em = datetime.now()
    solicitacao.pin_embarque = f"{secrets.randbelow(10000):04d}"
    atualizar_lotacao(solicitacao.carona)
    carona = solicitacao.carona
    notificar(solicitacao.passageiro, "vaga_confirmada", "Vaga confirmada!",
              f"{_primeiro_nome(carona.motorista)} confirmou sua vaga para {_quando(carona)}. "
              f"Seu PIN de embarque é {solicitacao.pin_embarque}.", carona)


def buscar_solicitacao(solicitacao_id: int) -> Solicitacao:
    solicitacao = db.session.get(Solicitacao, solicitacao_id)
    if solicitacao is None:
        raise ApiError("Solicitação não encontrada.", 404)
    return solicitacao


def pedir_vaga(carona: Carona, passageiro: Usuario, dados: PedidoVagaSchema) -> Solicitacao:
    # Regra: o motorista nao pode pedir vaga na propria carona
    if carona.motorista_id == passageiro.id:
        raise ApiError("O motorista não pode pedir vaga na própria carona.")
    exigir_email_verificado(passageiro, "pedir vaga")
    if carona.status == "lotada":
        raise ApiError("Esta carona está lotada.")
    if carona.status != "ativa" or carona.data_hora_saida <= datetime.now():
        raise ApiError("Esta carona não está mais recebendo pedidos.")

    # Regra: o passageiro nao pode pedir a mesma carona duas vezes.
    # Excecao: se ele mesmo cancelou o pedido, pode pedir de novo.
    solicitacao = next((s for s in carona.solicitacoes if s.passageiro_id == passageiro.id), None)
    if solicitacao is not None and solicitacao.status != "cancelada":
        raise ApiError("Você já pediu vaga nesta carona.", 409)
    if solicitacao is None:
        solicitacao = Solicitacao(carona=carona, passageiro=passageiro)
        db.session.add(solicitacao)

    solicitacao.status = "pendente"
    solicitacao.endereco_embarque = dados.endereco_embarque
    solicitacao.mensagem = dados.mensagem
    solicitacao.respondida_em = None
    solicitacao.pin_embarque = None
    solicitacao.expira_em = _prazo_resposta(carona)

    # [EXTRA] "Reserva imediata": o motorista aceita automaticamente
    if carona.reserva_automatica:
        _aceitar(solicitacao)
        notificar(carona.motorista, "novo_pedido", "Nova reserva confirmada",
                  f"{passageiro.nome} reservou uma vaga na sua carona de {_quando(carona)}.", carona)
    else:
        notificar(carona.motorista, "novo_pedido", "Novo pedido de vaga",
                  f"{passageiro.nome} pediu uma vaga na sua carona de {_quando(carona)}.", carona)

    db.session.commit()
    return solicitacao


def solicitacoes_da_carona(carona: Carona, usuario: Usuario) -> list[Solicitacao]:
    """Pedidos recebidos pelo motorista (tela "Motorista recebe o pedido")."""
    if carona.motorista_id != usuario.id:
        raise ApiError("Só o motorista pode ver os pedidos desta carona.", 403)
    expirar_vencidas(carona.solicitacoes)
    db.session.commit()
    return sorted(carona.solicitacoes, key=lambda s: s.id)


def solicitacoes_do_passageiro(usuario: Usuario, status: str | None = None) -> list[Solicitacao]:
    """ "Minhas caronas" do passageiro: os pedidos de vaga que ele fez."""
    consulta = (
        db.select(Solicitacao)
        .join(Solicitacao.carona)
        .where(Solicitacao.passageiro_id == usuario.id)
        .options(selectinload(Solicitacao.carona).selectinload(Carona.solicitacoes))
        .order_by(Carona.data_hora_saida.desc())
    )
    solicitacoes = list(db.session.scalars(consulta))
    expirar_vencidas(solicitacoes)
    db.session.commit()
    if status:
        solicitacoes = [s for s in solicitacoes if s.status == status]
    return solicitacoes


def _exigir_pendente_do_motorista(solicitacao: Solicitacao, usuario: Usuario) -> None:
    if solicitacao.carona.motorista_id != usuario.id:
        raise ApiError("Só o motorista pode responder a este pedido.", 403)
    expirar_vencidas([solicitacao])
    if solicitacao.status == "expirada":
        db.session.commit()
        raise ApiError("Este pedido expirou.")
    if solicitacao.status != "pendente":
        raise ApiError(f"Este pedido já está {solicitacao.status}.")


def aceitar_solicitacao(solicitacao: Solicitacao, usuario: Usuario) -> Solicitacao:
    _exigir_pendente_do_motorista(solicitacao, usuario)
    # Regra: nao pode haver mais passageiros aceitos do que vagas
    if solicitacao.carona.status != "ativa" or solicitacao.carona.vagas_restantes <= 0:
        raise ApiError("Não há vagas disponíveis nesta carona.")
    _aceitar(solicitacao)
    db.session.commit()
    return solicitacao


def recusar_solicitacao(solicitacao: Solicitacao, usuario: Usuario) -> Solicitacao:
    _exigir_pendente_do_motorista(solicitacao, usuario)
    solicitacao.status = "recusada"
    solicitacao.respondida_em = datetime.now()
    notificar(solicitacao.passageiro, "vaga_recusada", "Pedido não aceito",
              f"Sua vaga para {_quando(solicitacao.carona)} não foi confirmada. Que tal outra carona?",
              solicitacao.carona)
    db.session.commit()
    return solicitacao


def cancelar_solicitacao(solicitacao: Solicitacao, usuario: Usuario) -> Solicitacao:
    if solicitacao.passageiro_id != usuario.id:
        raise ApiError("Só o passageiro pode cancelar o próprio pedido.", 403)
    if solicitacao.status not in STATUS_SOLICITACAO_ATIVOS:
        raise ApiError(f"Este pedido já está {solicitacao.status}.")
    if solicitacao.carona.status not in STATUS_EDITAVEIS:
        raise ApiError("Não é possível cancelar depois que a viagem começou.")

    estava_aceita = solicitacao.status == "aceita"
    solicitacao.status = "cancelada"
    solicitacao.pin_embarque = None
    atualizar_lotacao(solicitacao.carona)  # libera a vaga (lotada -> ativa)
    if estava_aceita:
        notificar(solicitacao.carona.motorista, "pedido_cancelado", "Um passageiro desistiu",
                  f"{usuario.nome} desistiu da vaga de {_quando(solicitacao.carona)}. A vaga voltou para a busca.",
                  solicitacao.carona)
    db.session.commit()
    return solicitacao
