from caronauvv.ext.db import db

from .models import Notificacao

LIMITE_LISTA = 30


# ==========================================================
# CRIACAO (chamada pelos outros modulos quando algo acontece)
# Nao faz commit: entra na mesma transacao da acao que a gerou,
# entao se a acao falhar a notificacao tambem nao e gravada.
# ==========================================================
def notificar(usuario, tipo: str, titulo: str, texto: str, carona=None) -> Notificacao:
    notificacao = Notificacao(
        usuario_id=usuario.id,
        carona_id=carona.id if carona is not None else None,
        tipo=tipo,
        titulo=titulo[:120],
        texto=texto[:500],
    )
    db.session.add(notificacao)
    return notificacao


def notificar_admins(tipo: str, titulo: str, texto: str, carona=None) -> None:
    from caronauvv.auth.models import Usuario

    for admin in db.session.scalars(db.select(Usuario).where(Usuario.is_admin, Usuario.is_active)):
        notificar(admin, tipo, titulo, texto, carona)


# ==========================================================
# CONSULTA / LEITURA
# ==========================================================
def listar(usuario) -> tuple[list[Notificacao], int]:
    notificacoes = list(db.session.scalars(
        db.select(Notificacao)
        .where(Notificacao.usuario_id == usuario.id)
        .order_by(Notificacao.created_at.desc(), Notificacao.id.desc())
        .limit(LIMITE_LISTA)
    ))
    return notificacoes, contar_nao_lidas(usuario)


def contar_nao_lidas(usuario) -> int:
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Notificacao)
        .where(Notificacao.usuario_id == usuario.id, Notificacao.lida.is_(False))
    )


def marcar_todas_como_lidas(usuario) -> int:
    resultado = db.session.execute(
        db.update(Notificacao)
        .where(Notificacao.usuario_id == usuario.id, Notificacao.lida.is_(False))
        .values(lida=True)
    )
    db.session.commit()
    return resultado.rowcount
