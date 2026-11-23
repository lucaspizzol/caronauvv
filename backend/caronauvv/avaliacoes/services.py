import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal

from flask import has_request_context, request
from sqlalchemy.orm import selectinload

from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar

from .models import TAGS_MOTORISTA, TAGS_PASSAGEIRO, Avaliacao, AvaliacaoTag, Pagamento

PRAZO_AVALIAR = timedelta(days=14)  # como no BlaBlaCar: 14 dias para avaliar
NIVEIS = (  # (viagens minimas, nome do nivel de experiencia)
    (10, "Embaixador"),
    (3, "Veterano"),
    (0, "Calouro"),
)


# ==========================================================
# PIX "COPIA E COLA" (BR Code estatico do Banco Central)
# O passageiro paga direto ao motorista; a plataforma so gera o
# codigo (que vira o QR da tela 11) e guarda em pagamentos.pix_copia_cola.
# ==========================================================
def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _ascii(texto: str, limite: int) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento[:limite]


def _crc16(dados: str) -> str:
    # CRC16-CCITT (polinomio 0x1021, valor inicial 0xFFFF), exigido pelo BR Code
    crc = 0xFFFF
    for byte in dados.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def gerar_pix_copia_cola(chave: str, nome: str, cidade: str,
                         valor: Decimal | float | None = None, txid: str = "***") -> str:
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", chave)
    payload = (
        _campo("00", "01")
        + _campo("26", conta)
        + _campo("52", "0000")
        + _campo("53", "986")  # BRL
        + (_campo("54", f"{Decimal(str(valor)):.2f}") if valor is not None else "")
        + _campo("58", "BR")
        + _campo("59", _ascii(nome, 25))
        + _campo("60", _ascii(cidade, 15))
        + _campo("62", _campo("05", txid))
        + "6304"
    )
    return payload + _crc16(payload)


# ==========================================================
# AVALIACAO "AS CEGAS"
# A nota so aparece quando os dois lados avaliaram (ninguem avalia
# por vinganca) ou depois de X dias (configuracao dias_revelar_avaliacao).
# ==========================================================
def _dias_revelar() -> int:
    from caronauvv.admin.models import Configuracao
    return Configuracao.obter_int("dias_revelar_avaliacao", 7)


def avaliacao_revelada(avaliacao: Avaliacao, dias: int | None = None) -> bool:
    dias = _dias_revelar() if dias is None else dias
    if avaliacao.created_at <= datetime.now() - timedelta(days=dias):
        return True
    return any(a.avaliador_id == avaliacao.avaliado_id for a in avaliacao.solicitacao.avaliacoes)


def avaliacoes_reveladas(usuario, limite: int | None = None) -> list[Avaliacao]:
    from caronauvv.caronas.models import Solicitacao

    recebidas = db.session.scalars(
        db.select(Avaliacao)
        .where(Avaliacao.avaliado_id == usuario.id)
        .options(
            selectinload(Avaliacao.tags),
            selectinload(Avaliacao.solicitacao).selectinload(Solicitacao.avaliacoes),
        )
        .order_by(Avaliacao.created_at.desc(), Avaliacao.id.desc())
    )
    dias = _dias_revelar()
    reveladas = [a for a in recebidas if avaliacao_revelada(a, dias)]
    return reveladas[:limite] if limite else reveladas


# ==========================================================
# REPUTACAO (perfil publico, cartoes da busca e pedidos)
# Inspirada no BlaBlaCar: nota media, numero de viagens, nivel de
# experiencia, faltas, taxa de cancelamento e selos de confianca.
# ==========================================================
def _contar(consulta) -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))


def _calcular_reputacao(usuario) -> dict:
    from caronauvv.caronas.models import Carona, Solicitacao

    avaliacoes = avaliacoes_reveladas(usuario)
    notas = [a.nota for a in avaliacoes]
    nota_media = round(sum(notas) / len(notas), 1) if notas else None

    contagem_tags: dict[str, int] = {}
    for a in avaliacoes:
        for t in a.tags:
            contagem_tags[t.tag] = contagem_tags.get(t.tag, 0) + 1
    tags = sorted(contagem_tags.items(), key=lambda par: (-par[1], par[0]))[:4]

    viagens_motorista = _contar(db.select(Carona.id).where(
        Carona.motorista_id == usuario.id, Carona.status == "concluida"))
    caronas_oferecidas = _contar(db.select(Carona.id).where(Carona.motorista_id == usuario.id))
    canceladas = _contar(db.select(Carona.id).where(
        Carona.motorista_id == usuario.id, Carona.status == "cancelada"))
    viagens_passageiro = _contar(
        db.select(Solicitacao.id).join(Solicitacao.carona).where(
            Solicitacao.passageiro_id == usuario.id, Solicitacao.status == "aceita",
            Solicitacao.faltou.is_(False), Carona.status == "concluida"))
    faltas = _contar(db.select(Solicitacao.id).where(
        Solicitacao.passageiro_id == usuario.id, Solicitacao.faltou.is_(True)))

    viagens = viagens_motorista + viagens_passageiro
    nivel = next(nome for minimo, nome in NIVEIS if viagens >= minimo)
    if nivel == "Embaixador" and (nota_media or 0) < 4.5:
        nivel = "Veterano"

    selos = []
    if usuario.email_verificado:
        selos.append({"codigo": "email_uvv", "texto": "E-mail UVV confirmado"})
    if usuario.verificado:
        selos.append({"codigo": "perfil_verificado", "texto": "Perfil verificado pela UVV"})
    if usuario.identidade_verificada:
        selos.append({"codigo": "identidade_verificada", "texto": "Identidade verificada"})
    if usuario.cnh_verificada:
        selos.append({"codigo": "cnh_verificada", "texto": "CNH verificada"})
    if contagem_tags.get("Pontual", 0) >= 3:
        selos.append({"codigo": "pontual", "texto": "Super pontual"})
    if nota_media is not None and nota_media >= 4.8 and len(notas) >= 3:
        selos.append({"codigo": "bem_avaliado", "texto": "Muito bem avaliado"})
    if viagens_passageiro >= 3 and faltas == 0:
        selos.append({"codigo": "sem_faltas", "texto": "Nunca faltou"})

    return {
        "nota_media": nota_media,
        "total_avaliacoes": len(notas),
        "tags": [{"tag": t, "total": n} for t, n in tags],
        "viagens_motorista": viagens_motorista,
        "viagens_passageiro": viagens_passageiro,
        "faltas": faltas,
        "taxa_cancelamento": round(canceladas / caronas_oferecidas, 2) if caronas_oferecidas else 0.0,
        "nivel": nivel,
        "selos": selos,
    }


def reputacao(usuario) -> dict:
    # Guarda o resultado durante a requisicao (no environ, que e unico por
    # requisicao): a lista de caronas pode repetir o mesmo motorista varias vezes
    if not has_request_context():
        return _calcular_reputacao(usuario)
    cache = request.environ.setdefault("caronauvv.reputacoes", {})
    if usuario.id not in cache:
        cache[usuario.id] = _calcular_reputacao(usuario)
    return cache[usuario.id]


# ==========================================================
# AVALIAR (motorista <-> passageiro, depois da carona concluida)
# ==========================================================
def _papeis(solicitacao, usuario):
    """Devolve (avaliado, tags permitidas) conforme quem esta avaliando."""
    carona = solicitacao.carona
    if usuario.id == solicitacao.passageiro_id:
        return carona.motorista, TAGS_MOTORISTA
    if usuario.id == carona.motorista_id:
        return solicitacao.passageiro, TAGS_PASSAGEIRO
    raise ApiError("Só quem participou da viagem pode avaliar.", 403)


def avaliar(solicitacao, usuario, dados) -> Avaliacao:
    avaliado, tags_permitidas = _papeis(solicitacao, usuario)
    carona = solicitacao.carona
    if carona.status != "concluida":
        raise ApiError("Só dá para avaliar depois que a carona for concluída.")
    if solicitacao.status != "aceita" or solicitacao.faltou:
        raise ApiError("Este passageiro não viajou nesta carona.")
    if carona.concluida_em and carona.concluida_em < datetime.now() - PRAZO_AVALIAR:
        raise ApiError("O prazo para avaliar (14 dias) terminou.")
    if any(a.avaliador_id == usuario.id for a in solicitacao.avaliacoes):
        raise ApiError("Você já avaliou esta viagem.", 409)
    invalidas = [t for t in dados.tags if t not in tags_permitidas]
    if invalidas:
        raise ApiError(f"Tag não se aplica a esta avaliação: {', '.join(invalidas)}.")

    outro_lado_avaliou = any(a.avaliador_id == avaliado.id for a in solicitacao.avaliacoes)
    avaliacao = Avaliacao(
        solicitacao=solicitacao, avaliador_id=usuario.id, avaliado_id=avaliado.id,
        nota=dados.nota, comentario=dados.comentario,
    )
    avaliacao.tags = [AvaliacaoTag(tag=t) for t in dados.tags]
    db.session.add(avaliacao)

    notificar(
        avaliado, "nova_avaliacao", "Você recebeu uma avaliação",
        "As duas notas já estão no perfil de vocês." if outro_lado_avaliou
        else f"Avalie {usuario.nome.split()[0]} também para ver a sua nota.",
        carona,
    )
    db.session.commit()
    return avaliacao


def avaliacoes_pendentes(usuario) -> list[dict]:
    """Viagens concluidas (ultimos 14 dias) em que o usuario ainda nao avaliou o outro lado."""
    from caronauvv.caronas.models import Carona, Solicitacao

    limite = datetime.now() - PRAZO_AVALIAR
    consulta = (
        db.select(Solicitacao)
        .join(Solicitacao.carona)
        .where(
            Solicitacao.status == "aceita", Solicitacao.faltou.is_(False),
            Carona.status == "concluida", Carona.concluida_em >= limite,
            (Solicitacao.passageiro_id == usuario.id) | (Carona.motorista_id == usuario.id),
        )
        .options(selectinload(Solicitacao.avaliacoes))
        .order_by(Carona.data_hora_saida.desc())
    )
    pendentes = []
    for s in db.session.scalars(consulta):
        if any(a.avaliador_id == usuario.id for a in s.avaliacoes):
            continue
        avaliado, tags = _papeis(s, usuario)
        pendentes.append({
            "solicitacao_id": s.id,
            "papel_avaliado": "motorista" if avaliado.id == s.carona.motorista_id else "passageiro",
            "avaliado": {"id": avaliado.id, "nome": avaliado.nome, "curso": avaliado.curso, "foto_url": avaliado.foto_url},
            "carona": {
                "id": s.carona.id, "sentido": s.carona.sentido, "bairro_origem": s.carona.bairro_origem,
                "destino": s.carona.destino,
                "data_hora_saida": s.carona.data_hora_saida.isoformat(timespec="minutes"),
            },
            "tags_sugeridas": list(tags),
        })
    return pendentes


# ==========================================================
# PAGAMENTO DO RATEIO (Pix direto para o motorista)
# ==========================================================
def _exigir_participante(solicitacao, usuario) -> None:
    if usuario.id not in (solicitacao.passageiro_id, solicitacao.carona.motorista_id):
        raise ApiError("Só o motorista e o passageiro podem ver este pagamento.", 403)
    if solicitacao.status != "aceita":
        raise ApiError("O pagamento só existe para vagas confirmadas.")


def _reais(valor) -> str:
    return f"R$ {Decimal(valor):.2f}".replace(".", ",")


def obter_pix(solicitacao, usuario) -> Pagamento:
    _exigir_participante(solicitacao, usuario)
    carona = solicitacao.carona
    if not carona.valor_por_passageiro:
        raise ApiError("Esta carona é gratuita.")
    if solicitacao.pagamento is None:
        motorista = carona.motorista
        if not motorista.chave_pix:
            raise ApiError("O motorista ainda não cadastrou uma chave Pix. Combine o pagamento com ele.")
        solicitacao.pagamento = Pagamento(
            valor=carona.valor_por_passageiro, metodo="pix", status="pendente",
            pix_copia_cola=gerar_pix_copia_cola(
                motorista.chave_pix, motorista.nome, "Vila Velha", carona.valor_por_passageiro,
                txid=f"CARONAUVV{solicitacao.id}",
            ),
        )
        db.session.commit()
    return solicitacao.pagamento


def informar_pagamento(solicitacao, usuario, metodo: str = "pix") -> Pagamento:
    _exigir_participante(solicitacao, usuario)
    carona = solicitacao.carona
    if not carona.valor_por_passageiro:
        raise ApiError("Esta carona é gratuita.")
    if metodo not in ("pix", "dinheiro"):
        raise ApiError("Forma de pagamento inválida (pix ou dinheiro).")
    pagamento = solicitacao.pagamento
    if pagamento is None:
        pagamento = Pagamento(valor=carona.valor_por_passageiro, metodo=metodo)
        solicitacao.pagamento = pagamento
    if pagamento.status == "pago":
        raise ApiError("Este pagamento já foi registrado.")
    pagamento.metodo = metodo
    pagamento.status = "pago"
    pagamento.pago_em = datetime.now()
    if usuario.id == solicitacao.passageiro_id:
        notificar(carona.motorista, "pagamento_informado", "Pagamento informado",
                  f"{usuario.nome} informou que pagou {_reais(pagamento.valor)} ({metodo}).", carona)
    db.session.commit()
    return pagamento
