"""
FILA DO "PEDIR CARONA" (com prioridade)

1. O aluno entra na fila: bairro, sentido, dia e faixa de horario (max. 3 pedidos abertos).
2. Quando um motorista publica uma carona compativel (mesmo bairro, sem diferenciar acento;
   mesmo sentido; saida dentro da faixa), quem esta na fila e avisado, por ordem de chegada.
3. PRIORIDADE: nos primeiros `minutos_prioridade_fila` (15) minutos, so quem ja estava
   na fila consegue pedir vaga nessa carona. Se a carona tem reserva automatica, as vagas
   ficam guardadas para os primeiros da fila (posicao <= vagas livres) ate o fim da janela;
   depois a carona abre para todos.
4. Quem teve falta recente (nao apareceu numa viagem) perde a prioridade.
5. Quando o aluno consegue a vaga, o pedido vira "atendido". Passou a faixa, "expirado".
"""
from datetime import date, datetime, timedelta

from caronauvv.admin.models import Configuracao
from caronauvv.auth.models import Usuario
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.lugares.services import normalizar
from caronauvv.notificacoes.services import notificar

from .models import Carona, PedidoCarona, Solicitacao

MAX_ABERTOS = 3
DIAS_FALTA_SEM_PRIORIDADE = 30


# ==========================================================
# CONSULTAS AUXILIARES
# ==========================================================
def expirar_pedidos(pedidos=None) -> None:
    """Pedido aberto cuja faixa de horario ja passou vira "expirado" (o chamador faz o commit)."""
    agora = datetime.now()
    if pedidos is None:
        pedidos = db.session.scalars(
            db.select(PedidoCarona).where(PedidoCarona.status == "aberto", PedidoCarona.data <= agora.date())
        )
    for p in pedidos:
        if p.status == "aberto" and p.fim <= agora:
            p.status = "expirado"


def compativel(pedido: PedidoCarona, carona: Carona) -> bool:
    return (
        pedido.status == "aberto"
        and pedido.sentido == carona.sentido
        and pedido.bairro_chave == normalizar(carona.bairro_origem)
        and pedido.inicio <= carona.data_hora_saida <= pedido.fim
        and pedido.aluno_id != carona.motorista_id
    )


def _abertos_compativeis(carona: Carona) -> list[PedidoCarona]:
    """Pedidos abertos que combinam com a carona, por ordem de chegada."""
    candidatos = db.session.scalars(
        db.select(PedidoCarona)
        .where(PedidoCarona.status == "aberto", PedidoCarona.sentido == carona.sentido,
               PedidoCarona.data == carona.data_hora_saida.date(),
               PedidoCarona.bairro_chave == normalizar(carona.bairro_origem))
        .order_by(PedidoCarona.criado_em, PedidoCarona.id)
    )
    return [p for p in candidatos if compativel(p, carona)]


def teve_falta_recente(aluno_id: int) -> bool:
    desde = datetime.now() - timedelta(days=DIAS_FALTA_SEM_PRIORIDADE)
    return bool(db.session.scalar(
        db.select(db.func.count()).select_from(Solicitacao).join(Solicitacao.carona)
        .where(Solicitacao.passageiro_id == aluno_id, Solicitacao.faltou.is_(True),
               Carona.data_hora_saida >= desde)
    ))


def fila_da_carona(carona: Carona) -> list[PedidoCarona]:
    """Quem tem prioridade nesta carona: estava na fila antes dela ser publicada e sem falta recente."""
    criada = carona.created_at or datetime.now()
    return [p for p in _abertos_compativeis(carona)
            if p.criado_em <= criada and not teve_falta_recente(p.aluno_id)]


def posicao_na_fila(pedido: PedidoCarona) -> int:
    """1 = primeiro. Conta os pedidos abertos do mesmo bairro/sentido/dia, com faixa que se cruza, feitos antes."""
    antes = db.session.scalars(
        db.select(PedidoCarona)
        .where(PedidoCarona.status == "aberto", PedidoCarona.id != pedido.id,
               PedidoCarona.sentido == pedido.sentido, PedidoCarona.data == pedido.data,
               PedidoCarona.bairro_chave == pedido.bairro_chave,
               db.or_(PedidoCarona.criado_em < pedido.criado_em,
                      db.and_(PedidoCarona.criado_em == pedido.criado_em, PedidoCarona.id < pedido.id)))
    )
    return 1 + sum(1 for p in antes if p.hora_inicio < pedido.hora_fim and pedido.hora_inicio < p.hora_fim)


def demanda(bairro: str, sentido: str, saida: datetime) -> int:
    """Quantos alunos esperam carona deste bairro/sentido neste horario (mostrado ao motorista)."""
    chave = normalizar(bairro)
    if not chave:
        return 0
    pedidos = db.session.scalars(
        db.select(PedidoCarona).where(PedidoCarona.status == "aberto", PedidoCarona.sentido == sentido,
                                      PedidoCarona.data == saida.date(), PedidoCarona.bairro_chave == chave)
    )
    return sum(1 for p in pedidos if p.inicio <= saida <= p.fim and p.fim > datetime.now())


# ==========================================================
# CRIAR / LISTAR / CANCELAR
# ==========================================================
def criar_pedido(aluno: Usuario, dados) -> PedidoCarona:
    from caronauvv.auth.services import exigir_email_verificado

    exigir_email_verificado(aluno, "pedir carona")
    inicio = datetime.combine(dados.data, dados.hora_inicio)
    fim = datetime.combine(dados.data, dados.hora_fim)
    if fim <= datetime.now():
        raise ApiError("Essa faixa de horário já passou.", campos={"hora_fim": "Escolha um horário no futuro."})
    if dados.data > date.today() + timedelta(days=30):
        raise ApiError("Peça carona para até 30 dias à frente.", campos={"data": "Até 30 dias à frente."})
    if fim - inicio > timedelta(hours=4):
        raise ApiError("A faixa de horário pode ter no máximo 4 horas.", campos={"hora_fim": "No máximo 4 horas de faixa."})

    expirar_pedidos(db.session.scalars(
        db.select(PedidoCarona).where(PedidoCarona.aluno_id == aluno.id, PedidoCarona.status == "aberto")))
    abertos = db.session.scalars(
        db.select(PedidoCarona).where(PedidoCarona.aluno_id == aluno.id, PedidoCarona.status == "aberto")).all()
    if len(abertos) >= MAX_ABERTOS:
        raise ApiError(f"Você já tem {MAX_ABERTOS} pedidos de carona abertos. Cancele um para fazer outro.")
    chave = normalizar(dados.bairro)
    for p in abertos:
        if (p.bairro_chave, p.sentido, p.data) == (chave, dados.sentido, dados.data) and \
                p.hora_inicio < dados.hora_fim and dados.hora_inicio < p.hora_fim:
            raise ApiError("Você já está na fila para esse bairro e horário.", 409)

    pedido = PedidoCarona(aluno_id=aluno.id, bairro=dados.bairro, bairro_chave=chave, sentido=dados.sentido,
                          data=dados.data, hora_inicio=dados.hora_inicio, hora_fim=dados.hora_fim)
    db.session.add(pedido)
    db.session.commit()
    return pedido


def pedidos_do_aluno(aluno: Usuario) -> list[PedidoCarona]:
    pedidos = list(db.session.scalars(
        db.select(PedidoCarona).where(PedidoCarona.aluno_id == aluno.id)
        .order_by(PedidoCarona.data.desc(), PedidoCarona.hora_inicio.desc(), PedidoCarona.id.desc())
    ))
    expirar_pedidos(pedidos)
    db.session.commit()
    return pedidos


def buscar_pedido(pedido_id: int, aluno: Usuario) -> PedidoCarona:
    pedido = db.session.get(PedidoCarona, pedido_id)
    # Pedido de outro aluno responde 404 (nao revela que existe)
    if pedido is None or pedido.aluno_id != aluno.id:
        raise ApiError("Pedido de carona não encontrado.", 404)
    return pedido


def cancelar_pedido(pedido: PedidoCarona) -> PedidoCarona:
    if pedido.status != "aberto":
        raise ApiError(f"Este pedido já está {pedido.status}.")
    pedido.status = "cancelado"
    db.session.commit()
    return pedido


def pedido_to_dict(pedido: PedidoCarona) -> dict:
    dados = {
        "id": pedido.id, "bairro": pedido.bairro, "sentido": pedido.sentido,
        "data": pedido.data.isoformat(), "hora_inicio": pedido.hora_inicio.strftime("%H:%M"),
        "hora_fim": pedido.hora_fim.strftime("%H:%M"), "status": pedido.status,
        "criado_em": pedido.criado_em.isoformat(timespec="minutes"),
        "carona_id": pedido.carona_id, "posicao": None, "caronas_compativeis": 0,
        "sem_prioridade_por_falta": False,
    }
    if pedido.status == "aberto":
        dados["posicao"] = posicao_na_fila(pedido)
        dados["sem_prioridade_por_falta"] = teve_falta_recente(pedido.aluno_id)
        caronas = db.session.scalars(
            db.select(Carona).where(Carona.status == "ativa", Carona.sentido == pedido.sentido,
                                    Carona.data_hora_saida.between(max(pedido.inicio, datetime.now()), pedido.fim))
        )
        dados["caronas_compativeis"] = sum(1 for c in caronas if compativel(pedido, c))
    return dados


# ==========================================================
# INTEGRACAO COM AS CARONAS
# ==========================================================
def ao_publicar_carona(carona: Carona) -> int:
    """Chamado depois de criar a carona: liga a janela de prioridade e avisa a fila. Devolve quantos avisou."""
    fila = _abertos_compativeis(carona)
    if not fila:
        return 0
    minutos = Configuracao.obter_int("minutos_prioridade_fila", 15)
    carona.prioridade_ate = min(datetime.now() + timedelta(minutes=minutos), carona.data_hora_saida)
    ate = f"{carona.prioridade_ate:%H:%M}"
    quando = f"{carona.data_hora_saida:%d/%m} às {carona.data_hora_saida:%H:%M}"
    nome = carona.motorista.nome.split()[0]
    for posicao, pedido in enumerate(fila, start=1):
        if teve_falta_recente(pedido.aluno_id):
            texto = (f"{nome} vai sair de {carona.bairro_origem} {quando}. Por causa de uma falta recente, você "
                     f"não tem prioridade: a carona abre para todos às {ate}.")
        else:
            texto = (f"{nome} vai sair de {carona.bairro_origem} {quando}. Você é o {posicao}º da fila e tem "
                     f"prioridade para pedir vaga até {ate}.")
        notificar(pedido.aluno, "carona_da_fila", "Apareceu uma carona para você!", texto, carona)
    db.session.commit()
    return len(fila)


def checar_prioridade(carona: Carona, passageiro: Usuario) -> None:
    """Na janela de prioridade, so quem estava na fila pede vaga (e, com reserva automatica, na sua vez)."""
    if carona.prioridade_ate is None or carona.prioridade_ate <= datetime.now():
        return
    fila = fila_da_carona(carona)
    ate = f"{carona.prioridade_ate:%H:%M}"
    ids = [p.aluno_id for p in fila]
    if passageiro.id not in ids:
        raise ApiError(f"Esta carona está reservada para quem estava na fila do Pedir carona até as {ate}. "
                       "Tente de novo depois desse horário.", 403)
    if carona.reserva_automatica:
        # As vagas ficam guardadas para os primeiros da fila que ainda nao pediram
        ja_pediram = {s.passageiro_id for s in carona.solicitacoes if s.status in ("pendente", "aceita")}
        na_frente = [a for a in ids[:ids.index(passageiro.id)] if a not in ja_pediram]
        if len(na_frente) >= carona.vagas_restantes:
            raise ApiError(f"As vagas estão guardadas para quem chegou antes na fila até as {ate}. "
                           "Se não confirmarem, a carona abre para você depois desse horário.", 403)


def ao_confirmar_vaga(solicitacao: Solicitacao) -> None:
    """Conseguiu a vaga: o pedido de carona compativel do aluno vira "atendido" (sem commit)."""
    carona = solicitacao.carona
    pedidos = db.session.scalars(
        db.select(PedidoCarona).where(PedidoCarona.aluno_id == solicitacao.passageiro_id,
                                      PedidoCarona.status == "aberto")
    )
    for pedido in pedidos:
        if compativel(pedido, carona):
            pedido.status = "atendido"
            pedido.carona_id = carona.id
            pedido.atendido_em = datetime.now()
