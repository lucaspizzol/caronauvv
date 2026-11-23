import secrets
from datetime import datetime, timedelta

from sqlalchemy import or_

from caronauvv.caronas.models import Carona, PosicaoGps, Solicitacao
from caronauvv.caronas.services import STATUS_EM_ABERTO, participa
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar_admins

from .models import Alerta, Denuncia, LinkCompartilhado
from .schemas import DenunciaSchema, SosSchema

DURACAO_LINK_APOS_SAIDA = timedelta(hours=3)


# ==========================================================
# LINK DA FAMILIA (como o "Compartilhar status da viagem" do Uber)
# Qualquer pessoa com o link ve a viagem, sem precisar de conta.
# O link para de funcionar quando a viagem termina.
# ==========================================================
def compartilhar_viagem(carona: Carona, usuario) -> LinkCompartilhado:
    if not participa(carona, usuario):
        raise ApiError("Só o motorista e passageiros confirmados podem compartilhar a viagem.", 403)
    if carona.status not in STATUS_EM_ABERTO:
        raise ApiError("Só dá para compartilhar uma viagem que ainda não terminou.")

    existente = db.session.scalar(
        db.select(LinkCompartilhado).where(
            LinkCompartilhado.carona_id == carona.id, LinkCompartilhado.usuario_id == usuario.id,
            LinkCompartilhado.revogado_em.is_(None), LinkCompartilhado.expira_em > datetime.now(),
        )
    )
    if existente:
        return existente

    link = LinkCompartilhado(
        carona_id=carona.id, usuario_id=usuario.id, token=secrets.token_urlsafe(24),
        expira_em=carona.data_hora_saida + DURACAO_LINK_APOS_SAIDA,
    )
    db.session.add(link)
    db.session.commit()
    return link


def acompanhar(token: str) -> dict:
    link = db.session.scalar(db.select(LinkCompartilhado).where(LinkCompartilhado.token == token))
    if link is None:
        raise ApiError("Link não encontrado.", 404)
    carona = link.carona
    # A localizacao some quando a viagem termina (ou quando o link vence)
    if not link.ativo or carona.status in ("concluida", "cancelada"):
        raise ApiError("Esta viagem já terminou. O link não mostra mais a localização.", 410)

    link.acessos += 1
    db.session.commit()

    ultima = db.session.scalar(
        db.select(PosicaoGps).where(PosicaoGps.carona_id == carona.id)
        .order_by(PosicaoGps.registrada_em.desc()).limit(1)
    )
    motorista, veiculo = carona.motorista, carona.veiculo
    return {
        "compartilhado_por": link.usuario.nome,
        "status": carona.status,
        "sentido": carona.sentido,
        "origem": f"{carona.bairro_origem} - {carona.endereco_origem}",
        "destino": carona.destino,
        "data_hora_saida": carona.data_hora_saida.isoformat(timespec="minutes"),
        "iniciada_em": carona.iniciada_em.isoformat(timespec="minutes") if carona.iniciada_em else None,
        "motorista": {"nome": motorista.nome, "curso": motorista.curso, "verificado": motorista.verificado,
                      "foto_url": motorista.foto_url},   # a familia ve o rosto de quem esta dirigindo
        # A placa aparece para a familia: e o dado mais importante para seguranca
        "veiculo": veiculo.to_dict(com_placa=True) if veiculo else None,
        "ultima_posicao": (
            {"lat": ultima.lat, "lng": ultima.lng, "em": ultima.registrada_em.isoformat(timespec="minutes")}
            if ultima else None
        ),
        "expira_em": link.expira_em.isoformat(timespec="minutes"),
    }


# ==========================================================
# BOTAO DE EMERGENCIA ("Preciso de ajuda")
# Gera um alerta para a administracao; a tela tambem oferece
# ligar 190 e mandar o link da viagem aos contatos de confianca.
# ==========================================================
def acionar_sos(carona: Carona, usuario, dados: SosSchema) -> Alerta:
    if not participa(carona, usuario):
        raise ApiError("Só quem está na viagem pode acionar a emergência.", 403)
    if carona.status not in STATUS_EM_ABERTO:
        raise ApiError("Esta viagem já terminou.")
    alerta = Alerta(
        carona_id=carona.id, usuario_id=usuario.id, tipo="botao_panico",
        detalhe=dados.detalhe or "Botão de emergência acionado no app",
        lat=dados.lat, lng=dados.lng, resposta="preciso_ajuda",
        respondido_em=datetime.now(), status="aguardando",
    )
    db.session.add(alerta)
    notificar_admins("alerta_seguranca", "EMERGÊNCIA em uma carona",
                     f"{usuario.nome} acionou o botão de emergência na carona #{carona.id}.", carona)
    db.session.commit()
    return alerta


# ==========================================================
# DENUNCIAS
# Regra: so da para denunciar quem dividiu uma carona com voce
# (evita denuncias falsas contra qualquer aluno).
# ==========================================================
def dividiram_carona(usuario_a, usuario_b, carona_id: int | None = None) -> bool:
    consulta = (
        db.select(Solicitacao.id).join(Solicitacao.carona)
        .where(
            Solicitacao.status == "aceita",
            or_(
                (Solicitacao.passageiro_id == usuario_a.id) & (Carona.motorista_id == usuario_b.id),
                (Solicitacao.passageiro_id == usuario_b.id) & (Carona.motorista_id == usuario_a.id),
            ),
        )
    )
    if carona_id is not None:
        consulta = consulta.where(Carona.id == carona_id)
    return db.session.scalar(consulta.limit(1)) is not None


def denunciar(usuario, dados: DenunciaSchema) -> Denuncia:
    from caronauvv.auth.models import Usuario

    if dados.denunciado_id == usuario.id:
        raise ApiError("Você não pode denunciar a si mesmo.")
    denunciado = db.session.get(Usuario, dados.denunciado_id)
    if denunciado is None:
        raise ApiError("Usuário não encontrado.", 404)
    if not dividiram_carona(usuario, denunciado, dados.carona_id):
        raise ApiError("Você só pode denunciar alguém com quem dividiu uma carona.", 403)
    repetida = db.session.scalar(
        db.select(Denuncia.id).where(
            Denuncia.denunciante_id == usuario.id, Denuncia.denunciado_id == denunciado.id,
            Denuncia.status != "encerrada",
        ).limit(1)
    )
    if repetida:
        raise ApiError("Você já tem uma denúncia em análise contra esta pessoa.", 409)

    denuncia = Denuncia(
        denunciante_id=usuario.id, denunciado_id=denunciado.id, carona_id=dados.carona_id,
        motivo=dados.motivo, descricao=dados.descricao,
    )
    db.session.add(denuncia)
    motivo = dados.motivo.replace("_", " ")
    notificar_admins("alerta_seguranca", "Nova denúncia",
                     f"{usuario.nome} denunciou {denunciado.nome} ({motivo}).")
    db.session.commit()
    return denuncia
