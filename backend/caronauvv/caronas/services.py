import secrets
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import selectinload

from caronauvv.auth.models import Usuario, Veiculo
from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from .models import SENTIDOS, Carona, Solicitacao


CAMPOS_OBRIGATORIOS = ("bairro_origem", "endereco_origem", "data_hora_saida", "vagas")
CAMPOS_TEXTO = ("bairro_origem", "endereco_origem", "destino")
VAGAS_MIN, VAGAS_MAX = 1, 6
STATUS_EDITAVEIS = ("ativa", "lotada")
STATUS_SOLICITACAO_ATIVOS = ("pendente", "aceita")
PRAZO_RESPOSTA = timedelta(hours=2)  # pedido sem resposta expira 2 h antes da saida


# ==========================================================
# CONVERSAO / VALIDACAO DOS CAMPOS
# ==========================================================
def _texto(dados: dict, campo: str) -> str:
    valor = dados.get(campo)
    return str(valor).strip() if valor is not None else ""


def _inteiro(valor, campo: str) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ApiError(f"O campo {campo} precisa ser um número inteiro.")


def _decimal(valor, campo: str) -> Decimal:
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        raise ApiError(f"O campo {campo} precisa ser um número.")
    if not numero.is_finite():
        raise ApiError(f"O campo {campo} precisa ser um número.")
    return numero


def _data_hora(valor) -> datetime:
    try:
        data_hora = datetime.fromisoformat(str(valor))
    except ValueError:
        raise ApiError("data_hora_saida inválida (use AAAA-MM-DDTHH:MM).")
    # O banco guarda horario local sem fuso
    if data_hora.tzinfo is not None:
        data_hora = data_hora.astimezone().replace(tzinfo=None)
    return data_hora


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


def _aplicar_dados(carona: Carona, dados: dict, motorista: Usuario) -> None:
    """Valida e copia para a carona apenas os campos presentes em `dados`."""
    for campo in CAMPOS_TEXTO:
        if campo in dados:
            valor = _texto(dados, campo)
            if not valor:
                raise ApiError(f"O campo {campo} não pode ficar vazio.")
            setattr(carona, campo, valor)

    if "sentido" in dados:
        if dados["sentido"] not in SENTIDOS:
            raise ApiError(f"sentido deve ser um de: {', '.join(SENTIDOS)}.")
        carona.sentido = dados["sentido"]

    # Regra: nao e possivel criar carona com data/hora no passado
    if "data_hora_saida" in dados:
        saida = _data_hora(dados["data_hora_saida"])
        if saida <= datetime.now():
            raise ApiError("A data/hora de saída precisa ser no futuro.")
        carona.data_hora_saida = saida

    if "vagas" in dados:
        vagas = _inteiro(dados["vagas"], "vagas")
        if not VAGAS_MIN <= vagas <= VAGAS_MAX:
            raise ApiError(f"vagas deve ficar entre {VAGAS_MIN} e {VAGAS_MAX}.")
        aceitas = _aceitas(carona)
        if vagas < aceitas:
            raise ApiError(f"Já há {aceitas} passageiro(s) aceito(s); não dá para ter só {vagas} vaga(s).")
        carona.vagas = vagas

    if "valor_por_passageiro" in dados:
        valor = _decimal(dados["valor_por_passageiro"], "valor_por_passageiro")
        if valor < 0:
            raise ApiError("O valor por passageiro não pode ser negativo.")
        carona.valor_por_passageiro = valor.quantize(Decimal("0.01"))

    if "reserva_automatica" in dados:
        carona.reserva_automatica = bool(dados["reserva_automatica"])

    if "veiculo_id" in dados:
        if dados["veiculo_id"] is None:
            carona.veiculo_id = None
        else:
            veiculo = db.session.get(Veiculo, _inteiro(dados["veiculo_id"], "veiculo_id"))
            if veiculo is None or veiculo.usuario_id != motorista.id:
                raise ApiError("Veículo não encontrado entre os seus veículos.")
            carona.veiculo_id = veiculo.id

    for campo in ("origem_lat", "origem_lng", "distancia_km"):
        if campo in dados:
            valor = dados[campo]
            setattr(carona, campo, None if valor is None else float(_decimal(valor, campo)))

    if "duracao_min" in dados:
        valor = dados["duracao_min"]
        carona.duracao_min = None if valor is None else _inteiro(valor, "duracao_min")


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


def listar_caronas(filtros) -> list[Carona]:
    """
    Busca de caronas disponiveis: so status "ativa" e com saida no futuro.
    Filtros (query string): bairro, sentido, data (AAAA-MM-DD),
    hora_inicio e hora_fim (HH:MM). Sem data, a faixa de horario vale para hoje.
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
    if data or hora_inicio or hora_fim:
        dia = _data(data) if data else date.today()
        inicio = datetime.combine(dia, _hora(hora_inicio) if hora_inicio else time.min)
        fim = datetime.combine(dia, _hora(hora_fim) if hora_fim else time.max)
        consulta = consulta.where(Carona.data_hora_saida.between(inicio, fim))

    return list(db.session.scalars(consulta))


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
def criar_carona(motorista: Usuario, dados: dict) -> Carona:
    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if not _texto(dados, campo)]
    if faltando:
        raise ApiError(f"Campos obrigatórios: {', '.join(faltando)}.")

    carona = Carona(motorista_id=motorista.id, status="ativa")
    _aplicar_dados(carona, dados, motorista)
    db.session.add(carona)
    db.session.commit()
    return carona


def editar_carona(carona: Carona, usuario: Usuario, dados: dict) -> Carona:
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EDITAVEIS:
        raise ApiError(f"Não é possível editar uma carona {carona.status}.")

    _aplicar_dados(carona, dados, usuario)
    atualizar_lotacao(carona)
    db.session.commit()
    return carona


def cancelar_carona(carona: Carona, usuario: Usuario) -> Carona:
    _exigir_motorista(carona, usuario)
    if carona.status not in STATUS_EDITAVEIS:
        raise ApiError(f"Não é possível cancelar uma carona {carona.status}.")

    # Regra: cancelar a carona cancela as solicitacoes em aberto
    carona.status = "cancelada"
    carona.cancelada_em = datetime.now()
    for solicitacao in carona.solicitacoes:
        if solicitacao.status in STATUS_SOLICITACAO_ATIVOS:
            solicitacao.status = "cancelada"
    db.session.commit()
    return carona


def concluir_carona(carona: Carona, usuario: Usuario) -> Carona:
    """
    Funcionalidade 6 do MVP: depois do horario da viagem, o motorista marca a
    carona como concluida. O historico (passageiros aceitos) e mantido; pedidos
    que ficaram sem resposta passam para "expirada".
    """
    _exigir_motorista(carona, usuario)
    if carona.status not in ("ativa", "lotada", "em_andamento"):
        raise ApiError(f"Não é possível concluir uma carona {carona.status}.")
    if carona.data_hora_saida > datetime.now():
        raise ApiError("A carona só pode ser concluída depois do horário de saída.")

    carona.status = "concluida"
    carona.concluida_em = datetime.now()
    for solicitacao in carona.solicitacoes:
        if solicitacao.status == "pendente":
            solicitacao.status = "expirada"
    db.session.commit()
    return carona


# ==========================================================
# SOLICITACOES (pedido de vaga)
# ==========================================================
def _texto_opcional(dados: dict, campo: str, limite: int) -> str | None:
    valor = _texto(dados, campo)
    if len(valor) > limite:
        raise ApiError(f"O campo {campo} pode ter no máximo {limite} caracteres.")
    return valor or None


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


def buscar_solicitacao(solicitacao_id: int) -> Solicitacao:
    solicitacao = db.session.get(Solicitacao, solicitacao_id)
    if solicitacao is None:
        raise ApiError("Solicitação não encontrada.", 404)
    return solicitacao


def pedir_vaga(carona: Carona, passageiro: Usuario, dados: dict) -> Solicitacao:
    # Regra: o motorista nao pode pedir vaga na propria carona
    if carona.motorista_id == passageiro.id:
        raise ApiError("O motorista não pode pedir vaga na própria carona.")
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
    solicitacao.endereco_embarque = _texto_opcional(dados, "endereco_embarque", 255)
    solicitacao.mensagem = _texto_opcional(dados, "mensagem", 300)
    solicitacao.respondida_em = None
    solicitacao.pin_embarque = None
    solicitacao.expira_em = _prazo_resposta(carona)

    # [EXTRA] "Reserva imediata": o motorista aceita automaticamente
    if carona.reserva_automatica:
        _aceitar(solicitacao)

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
    db.session.commit()
    return solicitacao


def cancelar_solicitacao(solicitacao: Solicitacao, usuario: Usuario) -> Solicitacao:
    if solicitacao.passageiro_id != usuario.id:
        raise ApiError("Só o passageiro pode cancelar o próprio pedido.", 403)
    if solicitacao.status not in STATUS_SOLICITACAO_ATIVOS:
        raise ApiError(f"Este pedido já está {solicitacao.status}.")
    if solicitacao.carona.status not in STATUS_EDITAVEIS:
        raise ApiError("Não é possível cancelar depois que a viagem começou.")

    solicitacao.status = "cancelada"
    solicitacao.pin_embarque = None
    atualizar_lotacao(solicitacao.carona)  # libera a vaga (lotada -> ativa)
    db.session.commit()
    return solicitacao
