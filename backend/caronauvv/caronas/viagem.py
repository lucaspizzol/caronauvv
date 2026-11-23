"""
RESUMO DA VIAGEM (entrada, saida, tempo a bordo, distancia e medias)

- Entrada: hora do PIN de embarque (+ GPS do celular do motorista, se permitido).
- Saida: botao "Desembarcou" (motorista ou passageiro, com GPS opcional); ao concluir
  a viagem, quem ainda estava a bordo desembarca na hora da conclusao.
- Distancia: soma dos trechos da trilha GPS (formula de Haversine) entre a entrada e a saida.
Privacidade: so participantes e a administracao veem; o passageiro ve so a propria linha.
As trilhas sao apagadas depois de `dias_guardar_gps` dias (o resumo continua com os horarios).
"""
from datetime import datetime

from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.lugares.services import haversine_km

from .models import Carona, PosicaoGps, Solicitacao

MAX_PONTOS_MAPA = 500


def _iso(valor: datetime | None) -> str | None:
    return valor.isoformat(timespec="minutes") if valor else None


def _minutos(inicio: datetime | None, fim: datetime | None) -> int | None:
    if inicio is None or fim is None:
        return None
    return round((fim - inicio).total_seconds() / 60)


def trilha(carona: Carona) -> list[PosicaoGps]:
    return list(db.session.scalars(
        db.select(PosicaoGps).where(PosicaoGps.carona_id == carona.id).order_by(PosicaoGps.registrada_em, PosicaoGps.id)
    ))


def distancia_trilha_km(pontos: list[PosicaoGps], inicio: datetime | None = None, fim: datetime | None = None) -> float:
    """Soma dos trechos da trilha entre `inicio` e `fim` (km, 1 casa)."""
    escolhidos = [p for p in pontos if (inicio is None or p.registrada_em >= inicio)
                  and (fim is None or p.registrada_em <= fim)]
    total = sum(haversine_km(a.lat, a.lng, b.lat, b.lng) for a, b in zip(escolhidos, escolhidos[1:]))
    return round(total, 1)


def _ponto(lat: float | None, lng: float | None) -> dict | None:
    return {"lat": lat, "lng": lng} if lat is not None and lng is not None else None


def passageiro_dict(s: Solicitacao, pontos: list[PosicaoGps]) -> dict:
    a_bordo = _minutos(s.embarcou_em, s.desembarcou_em)
    km = distancia_trilha_km(pontos, s.embarcou_em, s.desembarcou_em) if s.embarcou_em and s.desembarcou_em else None
    return {
        "solicitacao_id": s.id, "nome": s.passageiro.nome, "faltou": s.faltou,
        "entrou_em": _iso(s.embarcou_em), "saiu_em": _iso(s.desembarcou_em),
        "entrada": _ponto(s.embarque_gps_lat, s.embarque_gps_lng),
        "saida": _ponto(s.desembarque_lat, s.desembarque_lng),
        "minutos_a_bordo": a_bordo, "km_a_bordo": km or None,
    }


def resumo_viagem(carona: Carona, usuario) -> dict:
    eh_motorista = carona.motorista_id == usuario.id
    minha = next((s for s in carona.solicitacoes if s.passageiro_id == usuario.id and s.status == "aceita"), None)
    if not (eh_motorista or minha or usuario.is_admin):
        raise ApiError("Só quem participou da viagem pode ver o resumo.", 403)

    pontos = trilha(carona)
    aceitos = [s for s in carona.solicitacoes if s.status == "aceita"]
    # O passageiro ve so a propria entrada/saida (nao a dos colegas)
    visiveis = aceitos if (eh_motorista or usuario.is_admin) else [minha]

    duracao = _minutos(carona.iniciada_em, carona.concluida_em)
    km = distancia_trilha_km(pontos) if len(pontos) > 1 else None
    velocidade = round(km / (duracao / 60), 1) if km and duracao and duracao > 0 else None
    passo = max(1, len(pontos) // MAX_PONTOS_MAPA)
    return {
        "carona_id": carona.id, "status": carona.status,
        "saida_prevista": _iso(carona.data_hora_saida), "iniciada_em": _iso(carona.iniciada_em),
        "concluida_em": _iso(carona.concluida_em),
        "atraso_saida_min": _minutos(carona.data_hora_saida, carona.iniciada_em),
        "duracao_min": duracao,
        "distancia_km": km if km else carona.distancia_km,
        "distancia_pela_trilha": bool(km),
        "velocidade_media_kmh": velocidade,
        "trilha": [[p.lat, p.lng] for p in pontos[::passo]],
        "passageiros": [passageiro_dict(s, pontos) for s in visiveis],
    }


def medias_das_viagens() -> dict:
    """Para o painel da administracao: medias das viagens concluidas que foram iniciadas no app."""
    caronas = list(db.session.scalars(
        db.select(Carona).where(Carona.status == "concluida", Carona.iniciada_em.is_not(None),
                                Carona.concluida_em.is_not(None))
    ))
    duracoes = [d for c in caronas if (d := _minutos(c.iniciada_em, c.concluida_em)) is not None and d > 0]
    atrasos = [_minutos(c.data_hora_saida, c.iniciada_em) for c in caronas]
    velocidades = []
    for c in caronas:
        d = _minutos(c.iniciada_em, c.concluida_em)
        km = distancia_trilha_km(trilha(c)) or c.distancia_km
        if km and d and d > 0:
            velocidades.append(km / (d / 60))
    a_bordo = [m for c in caronas for s in c.solicitacoes
               if (m := _minutos(s.embarcou_em, s.desembarcou_em)) is not None]

    def media(valores):
        return round(sum(valores) / len(valores), 1) if valores else None

    return {
        "viagens_medidas": len(caronas),
        "tempo_medio_viagem_min": media(duracoes),
        "atraso_medio_saida_min": media(atrasos),
        "velocidade_media_kmh": media(velocidades),
        "tempo_medio_a_bordo_min": media(a_bordo),
    }


def registrar_desembarque(solicitacao: Solicitacao, usuario, lat: float | None, lng: float | None) -> Solicitacao:
    """Motorista ou o proprio passageiro marca que ele desceu do carro."""
    from caronauvv.notificacoes.services import notificar

    carona = solicitacao.carona
    eh_motorista = carona.motorista_id == usuario.id
    if not (eh_motorista or solicitacao.passageiro_id == usuario.id):
        raise ApiError("Só o motorista ou o próprio passageiro registram o desembarque.", 403)
    if carona.status != "em_andamento":
        raise ApiError("O desembarque só é registrado com a viagem em andamento.")
    if solicitacao.embarcou_em is None:
        raise ApiError("Este passageiro ainda não embarcou.")
    if solicitacao.desembarcou_em is not None:
        raise ApiError("O desembarque já foi registrado.")
    solicitacao.desembarcou_em = datetime.now()
    solicitacao.desembarque_lat, solicitacao.desembarque_lng = lat, lng
    if eh_motorista:
        notificar(solicitacao.passageiro, "desembarque", "Você chegou!",
                  "O motorista registrou seu desembarque. Não esqueça de avaliar a viagem depois.", carona)
    else:
        notificar(carona.motorista, "desembarque", "Passageiro desembarcou",
                  f"{solicitacao.passageiro.nome.split()[0]} registrou que desceu do carro.", carona)
    db.session.commit()
    return solicitacao
