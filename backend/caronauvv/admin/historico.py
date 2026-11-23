"""
HISTORICO DA ADMINISTRACAO
Cada acao de moderacao vira uma linha em acoes_admin, gravada na mesma
transacao da propria acao: se a acao falhar, o registro tambem nao fica.
"""
from datetime import datetime, timedelta
from typing import Optional

from caronauvv.auth.models import Usuario
from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from .models import ACOES_ADMIN, AcaoAdmin


def registrar_acao(admin: Optional[Usuario], acao: str, alvo: Optional[Usuario] = None,
                   detalhe: Optional[str] = None) -> AcaoAdmin:
    """Adiciona a acao na sessao (quem chama faz o commit junto com a mudanca)."""
    registro = AcaoAdmin(
        admin_id=admin.id if admin else None, acao=acao,
        alvo_id=alvo.id if alvo else None, alvo_nome=alvo.nome[:120] if alvo else None,
        detalhe=(detalhe or "")[:300] or None,
    )
    db.session.add(registro)
    return registro


def listar_acoes(acao: str = "", dias: int = 30, limite: int = 200) -> list[AcaoAdmin]:
    if acao and acao not in ACOES_ADMIN:
        raise ApiError(f"acao deve ser uma de: {', '.join(ACOES_ADMIN)}.")
    consulta = (db.select(AcaoAdmin)
                .where(AcaoAdmin.created_at >= datetime.now() - timedelta(days=max(1, min(dias, 365))))
                .order_by(AcaoAdmin.created_at.desc(), AcaoAdmin.id.desc())
                .limit(max(1, min(limite, 500))))
    if acao:
        consulta = consulta.where(AcaoAdmin.acao == acao)
    return list(db.session.scalars(consulta))
