"""
CONTROLE DE AVALIACOES (moderacao automatica)

Toda avaliacao nova passa por aqui, na mesma transacao em que e gravada:

1. Nota abaixo de `nota_alerta_avaliacao` (padrao 4): cria um alerta "avaliacao_baixa"
   no painel e avisa os administradores na hora (sino de notificacoes).
2. Media de quem foi avaliado abaixo de `media_minima_usuario` (padrao 3), com pelo
   menos `avaliacoes_minimas_exclusao` avaliacoes recebidas: a conta e excluida do
   aplicativo automaticamente (suspensa: o login para de funcionar, caronas futuras e
   pedidos em aberto sao cancelados) e a administracao recebe um alerta.

A media usada aqui e a de TODAS as avaliacoes recebidas (inclusive as que o aluno
ainda nao ve por causa da avaliacao "as cegas"): a administracao enxerga tudo.
Administradores nunca sao excluidos automaticamente. A exclusao e uma suspensao,
nao apaga dados: a administracao pode reativar a conta no painel se achar injusto.
"""
from datetime import datetime

from caronauvv.admin.models import Configuracao
from caronauvv.email import enviar_email
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar, notificar_admins

from .models import Avaliacao


def limites() -> dict:
    return {
        "nota_alerta": Configuracao.obter_decimal("nota_alerta_avaliacao", "4"),
        "media_minima": Configuracao.obter_decimal("media_minima_usuario", "3"),
        "minimo_avaliacoes": Configuracao.obter_int("avaliacoes_minimas_exclusao", 1),
    }


def media_recebida(usuario_id: int) -> tuple[float | None, int]:
    """(media, quantidade) de todas as avaliacoes que o usuario recebeu."""
    media, total = db.session.execute(
        db.select(db.func.avg(Avaliacao.nota), db.func.count(Avaliacao.id)).where(Avaliacao.avaliado_id == usuario_id)
    ).one()
    return (round(float(media), 2) if media is not None else None), int(total)


def suspender_conta(usuario, motivo: str) -> None:
    """
    Tira o usuario do aplicativo (sem apagar nada): o login deixa de funcionar na hora,
    as caronas futuras dele sao canceladas (passageiros avisados) e os pedidos de vaga
    e da fila "Pedir carona" em aberto sao cancelados (as vagas voltam para os outros).
    Usado pela exclusao automatica e pela suspensao manual do painel.
    """
    from caronauvv.caronas.models import PedidoCarona, Solicitacao

    usuario.is_active = False
    usuario.suspenso_em = datetime.now()
    usuario.suspenso_motivo = motivo[:255]

    for carona in usuario.caronas_oferecidas:
        if carona.status in ("ativa", "lotada"):
            carona.status = "cancelada"
            carona.cancelada_em = datetime.now()
            for s in carona.solicitacoes:
                if s.status in ("pendente", "aceita"):
                    s.status = "cancelada"
                    s.pin_embarque = None
                    notificar(s.passageiro, "carona_cancelada", "Carona cancelada",
                              "A carona foi cancelada pela administração. Busque outra opção.", carona)

    abertas = db.session.scalars(db.select(Solicitacao).where(
        Solicitacao.passageiro_id == usuario.id, Solicitacao.status.in_(("pendente", "aceita"))))
    for s in abertas:
        if s.carona.status in ("ativa", "lotada"):
            s.status = "cancelada"
            s.pin_embarque = None
            from caronauvv.caronas.services import atualizar_lotacao
            atualizar_lotacao(s.carona)
            notificar(s.carona.motorista, "pedido_cancelado", "Passageiro removido",
                      f"{usuario.nome.split()[0]} foi removido(a) pela administração; a vaga voltou a ficar livre.", s.carona)

    for pedido in db.session.scalars(db.select(PedidoCarona).where(
            PedidoCarona.aluno_id == usuario.id, PedidoCarona.status == "aberto")):
        pedido.status = "cancelado"


def moderar_avaliacao(avaliacao: Avaliacao) -> None:
    """Chamada logo depois de gravar a avaliacao (antes do commit)."""
    from caronauvv.seguranca.models import Alerta

    db.session.flush()   # a nova nota entra na media
    regras = limites()
    avaliado, avaliador = avaliacao.avaliado, avaliacao.avaliador
    carona = avaliacao.solicitacao.carona
    papel = "motorista" if avaliado.id == carona.motorista_id else "passageiro"

    if avaliacao.nota < regras["nota_alerta"]:
        detalhe = f"Nota {avaliacao.nota} de {avaliador.nome} para {avaliado.nome} ({papel})"
        if avaliacao.comentario:
            detalhe += f': "{avaliacao.comentario}"'
        db.session.add(Alerta(carona=carona, usuario=avaliado, tipo="avaliacao_baixa", detalhe=detalhe[:300]))
        notificar_admins("avaliacao_baixa", f"Avaliação baixa: nota {avaliacao.nota}",
                         f"{avaliado.nome} ({papel}) recebeu nota {avaliacao.nota} de {avaliador.nome}.", carona)

    media, total = media_recebida(avaliado.id)
    if (avaliado.is_active and not avaliado.is_admin and media is not None
            and total >= regras["minimo_avaliacoes"] and media < regras["media_minima"]):
        media_br = f"{media:.1f}".replace(".", ",")
        minima_br = f"{regras['media_minima']:.1f}".replace(".", ",")
        suspender_conta(avaliado, f"Exclusão automática: média {media_br} em {total} avaliação(ões) (mínimo {minima_br}).")
        db.session.add(Alerta(
            carona=carona, usuario=avaliado, tipo="exclusao_automatica",
            detalhe=f"{avaliado.nome} ({papel}) foi excluído(a) automaticamente: média {media_br} em {total} avaliação(ões)."[:300],
        ))
        notificar_admins("exclusao_automatica", "Usuário excluído automaticamente",
                         f"{avaliado.nome} ficou com média {media_br} (abaixo de {minima_br}) e foi removido(a) do aplicativo.",
                         carona)
        enviar_email(
            avaliado.email, "CaronaUVV - sua conta foi suspensa",
            f"Olá, {avaliado.nome.split()[0]}. Sua média de avaliações ficou em {media_br}, abaixo do mínimo de "
            f"{minima_br} exigido pelo CaronaUVV, e sua conta foi suspensa automaticamente. Se achar que houve "
            "engano, procure a administração.",
        )
