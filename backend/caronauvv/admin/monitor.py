"""
MONITOR DO PAINEL (tempo real)

- viagens_ao_vivo(): todas as viagens acontecendo agora, as que saem nas proximas horas e
  as que terminaram ha pouco, com motorista, carro e placa, passageiros (aguardando,
  a bordo, desembarcou, faltou), ultima posicao do GPS, velocidade e trilha para o mapa.
- avaliacoes_ao_vivo(): feed das avaliacoes (todas, inclusive as que o aluno ainda nao
  ve por causa da avaliacao "as cegas"), estatisticas, distribuicao das notas, alunos em
  risco (media perto do limite) e excluidos automaticamente.

O front consulta as duas rotas a cada poucos segundos (composable useAoVivo).
So administradores acessam (decorator @admin_required nas rotas).
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import selectinload

from caronauvv.auth.models import Usuario
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.avaliacoes.moderacao import limites
from caronauvv.avaliacoes.services import avaliacao_revelada
from caronauvv.caronas.models import Carona, PosicaoGps, Solicitacao
from caronauvv.ext.db import db
from caronauvv.lugares.services import haversine_km
from caronauvv.seguranca.models import Alerta

JANELA_ANTES = timedelta(hours=3)    # viagens que saem nas proximas 3 h
JANELA_DEPOIS = timedelta(hours=3)   # viagens concluidas ha ate 3 h
MAX_PONTOS = 300


def _iso(valor: datetime | None) -> str | None:
    return valor.isoformat(timespec="seconds") if valor else None


def _pessoa(u: Usuario) -> dict:
    return {"id": u.id, "nome": u.nome, "foto_url": u.foto_url, "telefone": u.telefone, "is_active": u.is_active}


def _situacao_passageiro(s: Solicitacao) -> str:
    if s.faltou:
        return "faltou"
    if s.desembarcou_em:
        return "desembarcou"
    if s.embarcou_em:
        return "a_bordo"
    return "aguardando"


def _velocidade_kmh(pontos: list[PosicaoGps]) -> float | None:
    """Velocidade entre os dois ultimos pontos do GPS."""
    if len(pontos) < 2:
        return None
    a, b = pontos[-2], pontos[-1]
    horas = (b.registrada_em - a.registrada_em).total_seconds() / 3600
    if horas <= 0:
        return None
    return round(haversine_km(a.lat, a.lng, b.lat, b.lng) / horas, 1)


def viagens_ao_vivo(agora: datetime | None = None) -> dict:
    agora = agora or datetime.now()
    caronas = list(db.session.scalars(
        db.select(Carona)
        .options(selectinload(Carona.solicitacoes).selectinload(Solicitacao.passageiro),
                 selectinload(Carona.motorista), selectinload(Carona.veiculo))
        .where(db.or_(
            Carona.status == "em_andamento",
            db.and_(Carona.status.in_(("ativa", "lotada")), Carona.data_hora_saida.between(agora - JANELA_ANTES, agora + JANELA_ANTES)),
            db.and_(Carona.status == "concluida", Carona.concluida_em >= agora - JANELA_DEPOIS),
        ))
        .order_by(Carona.data_hora_saida)
    ))
    ids = [c.id for c in caronas]
    trilhas: dict[int, list[PosicaoGps]] = {i: [] for i in ids}
    if ids:
        for p in db.session.scalars(db.select(PosicaoGps).where(PosicaoGps.carona_id.in_(ids))
                                    .order_by(PosicaoGps.registrada_em, PosicaoGps.id)):
            trilhas[p.carona_id].append(p)
    alertas_abertos: dict[int, int] = dict(db.session.execute(
        db.select(Alerta.carona_id, db.func.count()).where(Alerta.carona_id.in_(ids), Alerta.status != "resolvido")
        .group_by(Alerta.carona_id)
    ).all()) if ids else {}

    viagens = []
    for c in caronas:
        pontos = trilhas[c.id][-MAX_PONTOS:]
        ultima = pontos[-1] if pontos else None
        passageiros = [s for s in c.solicitacoes if s.status == "aceita"]
        viagens.append({
            "id": c.id,
            "status": c.status,
            "sentido": c.sentido,
            "bairro_origem": c.bairro_origem,
            "endereco_origem": c.endereco_origem,
            "destino": c.destino,
            "data_hora_saida": _iso(c.data_hora_saida),
            "iniciada_em": _iso(c.iniciada_em),
            "concluida_em": _iso(c.concluida_em),
            "minutos_em_viagem": round((agora - c.iniciada_em).total_seconds() / 60) if c.status == "em_andamento" and c.iniciada_em else None,
            "motorista": _pessoa(c.motorista),
            "veiculo": c.veiculo.to_dict(com_placa=True) if c.veiculo else None,
            "passageiros": [{
                **_pessoa(s.passageiro),
                "solicitacao_id": s.id,
                "situacao": _situacao_passageiro(s),
                "entrou_em": _iso(s.embarcou_em),
                "saiu_em": _iso(s.desembarcou_em),
            } for s in passageiros],
            "ultima_posicao": {"lat": ultima.lat, "lng": ultima.lng, "em": _iso(ultima.registrada_em),
                               "segundos_atras": int((agora - ultima.registrada_em).total_seconds())} if ultima else None,
            "velocidade_kmh": _velocidade_kmh(pontos) if c.status == "em_andamento" else None,
            "trilha": [[p.lat, p.lng] for p in pontos],
            "alertas_abertos": alertas_abertos.get(c.id, 0),
        })
    contagem = {s: sum(1 for v in viagens if v["status"] == s) for s in ("em_andamento", "ativa", "lotada", "concluida")}
    return {
        "atualizado_em": _iso(agora),
        "viagens": viagens,
        "totais": {
            "em_andamento": contagem["em_andamento"],
            "saindo_em_breve": contagem["ativa"] + contagem["lotada"],
            "concluidas_recentes": contagem["concluida"],
            "passageiros_a_bordo": sum(1 for v in viagens for p in v["passageiros"] if p["situacao"] == "a_bordo"),
        },
    }


def _avaliacao_admin(a: Avaliacao) -> dict:
    carona = a.solicitacao.carona
    return {
        "id": a.id,
        "nota": a.nota,
        "comentario": a.comentario,
        "tags": [t.tag for t in a.tags],
        "criada_em": _iso(a.created_at),
        "revelada": avaliacao_revelada(a),
        "papel_avaliado": "motorista" if a.avaliado_id == carona.motorista_id else "passageiro",
        "avaliador": {"id": a.avaliador.id, "nome": a.avaliador.nome, "foto_url": a.avaliador.foto_url},
        "avaliado": {"id": a.avaliado.id, "nome": a.avaliado.nome, "foto_url": a.avaliado.foto_url,
                     "is_active": a.avaliado.is_active},
        "carona": {"id": carona.id, "bairro_origem": carona.bairro_origem, "destino": carona.destino,
                   "sentido": carona.sentido, "data_hora_saida": _iso(carona.data_hora_saida)},
    }


def avaliacoes_ao_vivo(nota_maxima: int | None = None, limite: int = 60) -> dict:
    regras = limites()
    consulta = (
        db.select(Avaliacao)
        .options(selectinload(Avaliacao.tags), selectinload(Avaliacao.avaliador), selectinload(Avaliacao.avaliado),
                 selectinload(Avaliacao.solicitacao).selectinload(Solicitacao.carona),
                 selectinload(Avaliacao.solicitacao).selectinload(Solicitacao.avaliacoes))
        .order_by(Avaliacao.created_at.desc(), Avaliacao.id.desc())
        .limit(max(1, min(limite, 200)))
    )
    if nota_maxima is not None:
        consulta = consulta.where(Avaliacao.nota <= nota_maxima)
    feed = [_avaliacao_admin(a) for a in db.session.scalars(consulta)]

    total, media = db.session.execute(db.select(db.func.count(Avaliacao.id), db.func.avg(Avaliacao.nota))).one()
    distribuicao = {str(n): 0 for n in range(1, 6)}
    for nota, qtd in db.session.execute(db.select(Avaliacao.nota, db.func.count()).group_by(Avaliacao.nota)):
        distribuicao[str(nota)] = qtd
    ultimas_24h = db.session.scalar(db.select(db.func.count(Avaliacao.id))
                                    .where(Avaliacao.created_at >= datetime.now() - timedelta(hours=24)))

    # Media de cada aluno avaliado: os que estao perto (ou abaixo) do limite aparecem primeiro
    por_usuario = db.session.execute(
        db.select(Avaliacao.avaliado_id, db.func.avg(Avaliacao.nota), db.func.count(Avaliacao.id))
        .group_by(Avaliacao.avaliado_id)
        .order_by(db.func.avg(Avaliacao.nota))
    ).all()
    usuarios = {u.id: u for u in db.session.scalars(db.select(Usuario).where(Usuario.id.in_([r[0] for r in por_usuario])))} if por_usuario else {}
    em_risco = []
    for usuario_id, media_u, qtd in por_usuario:
        media_u = round(float(media_u), 2)
        if media_u >= float(regras["nota_alerta"]):
            continue
        u = usuarios[usuario_id]
        em_risco.append({"id": u.id, "nome": u.nome, "foto_url": u.foto_url, "media": media_u, "avaliacoes": qtd,
                         "is_active": u.is_active, "suspenso_motivo": u.suspenso_motivo})

    excluidos = db.session.scalars(
        db.select(Usuario).where(Usuario.suspenso_motivo.like("Exclusão automática%")).order_by(Usuario.suspenso_em.desc())
    )
    alertas_abertos = db.session.scalar(db.select(db.func.count(Alerta.id)).where(
        Alerta.tipo == "avaliacao_baixa", Alerta.status != "resolvido"))
    return {
        "regras": {k: float(v) for k, v in regras.items()},
        "estatisticas": {
            "total": total,
            "media_geral": round(float(media), 2) if media is not None else None,
            "ultimas_24h": ultimas_24h,
            "distribuicao": distribuicao,
            "alertas_abertos": alertas_abertos,
        },
        "avaliacoes": feed,
        "em_risco": em_risco[:15],
        "excluidos": [{"id": u.id, "nome": u.nome, "foto_url": u.foto_url, "suspenso_em": _iso(u.suspenso_em),
                       "motivo": u.suspenso_motivo, "is_active": u.is_active} for u in excluidos],
    }
