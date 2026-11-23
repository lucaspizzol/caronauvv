"""
PAINEL DA ADMINISTRACAO
Indicadores, moderacao (denuncias, suspensao, selo de verificado),
alertas de seguranca, demanda sem oferta e configuracoes.
"""
from datetime import datetime, timedelta

from sqlalchemy import inspect

from caronauvv.auth.models import Usuario
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.caronas.models import Carona, Solicitacao
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar
from caronauvv.seguranca.models import STATUS_DENUNCIA, Alerta, Denuncia

from .models import Busca, Configuracao

KG_CO2_POR_KM = 0.12  # emissao media de um carro popular (kg de CO2 por km)


def _contar(modelo, *condicoes) -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(modelo).where(*condicoes))


# ==========================================================
# INDICADORES (KPIs)
# ==========================================================
def resumo() -> dict:
    agora = datetime.now()

    por_status = dict(db.session.execute(
        db.select(Carona.status, db.func.count()).group_by(Carona.status)
    ).all())

    # Ocupacao das viagens concluidas: assentos usados / assentos oferecidos
    concluidas = list(db.session.scalars(db.select(Carona).where(Carona.status == "concluida")))
    assentos = sum(c.vagas for c in concluidas)
    passageiros_viajaram = sum(
        1 for c in concluidas for s in c.solicitacoes if s.status == "aceita" and not s.faltou
    )
    km_compartilhados = sum(
        (c.distancia_km or 0) * sum(1 for s in c.solicitacoes if s.status == "aceita" and not s.faltou)
        for c in concluidas
    )

    nota_geral = db.session.scalar(db.select(db.func.avg(Avaliacao.nota)))
    falta = _contar(Solicitacao, Solicitacao.faltou.is_(True))
    aceitas = _contar(Solicitacao, Solicitacao.status == "aceita")

    # Demanda sem oferta: bairros mais buscados que nao tiveram resultado (ultimos 30 dias)
    sem_resultado = db.session.execute(
        db.select(Busca.bairro, db.func.count().label("buscas"))
        .where(Busca.qtd_resultados == 0, Busca.created_at >= agora - timedelta(days=30))
        .group_by(Busca.bairro)
        .order_by(db.func.count().desc())
        .limit(5)
    ).all()
    bairros_oferta = db.session.execute(
        db.select(Carona.bairro_origem, db.func.count().label("caronas"))
        .group_by(Carona.bairro_origem)
        .order_by(db.func.count().desc())
        .limit(5)
    ).all()

    return {
        "usuarios": {
            "total": _contar(Usuario),
            "ativos_30_dias": _contar(Usuario, Usuario.ultimo_login_em >= agora - timedelta(days=30)),
            "verificados": _contar(Usuario, Usuario.verificado.is_(True)),
            "suspensos": _contar(Usuario, Usuario.is_active.is_(False)),
            "verificacoes_pendentes": _contar(
                Usuario, Usuario.verificacao_solicitada_em.is_not(None), Usuario.verificado.is_(False)),
        },
        "caronas": {"total": sum(por_status.values()), "por_status": por_status},
        "viagens": {
            "concluidas": len(concluidas),
            "passageiros_transportados": passageiros_viajaram,
            "taxa_ocupacao": round(passageiros_viajaram / assentos, 2) if assentos else 0.0,
            "km_compartilhados": round(km_compartilhados, 1),
            "co2_evitado_kg": round(km_compartilhados * KG_CO2_POR_KM, 1),
            "taxa_faltas": round(falta / aceitas, 2) if aceitas else 0.0,
        },
        "confianca": {
            "nota_media": round(float(nota_geral), 2) if nota_geral is not None else None,
            "avaliacoes": _contar(Avaliacao),
            "denuncias_abertas": _contar(Denuncia, Denuncia.status != "encerrada"),
            "alertas_aguardando": _contar(Alerta, Alerta.status != "resolvido"),
        },
        "demanda_sem_oferta": [{"bairro": b, "buscas": n} for b, n in sem_resultado],
        "bairros_com_mais_oferta": [{"bairro": b, "caronas": n} for b, n in bairros_oferta],
    }


# ==========================================================
# USUARIOS: verificacao (selo) e suspensao
# ==========================================================
def listar_usuarios(busca: str = "", so_pendentes: bool = False) -> list[Usuario]:
    consulta = db.select(Usuario).order_by(Usuario.verificacao_solicitada_em.desc().nulls_last(), Usuario.nome)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(
            Usuario.nome.ilike(termo) | Usuario.email.ilike(termo) | Usuario.matricula.ilike(termo))
    if so_pendentes:
        consulta = consulta.where(Usuario.verificacao_solicitada_em.is_not(None), Usuario.verificado.is_(False))
    return list(db.session.scalars(consulta.limit(100)))


def _usuario(usuario_id: int) -> Usuario:
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        raise ApiError("Usuário não encontrado.", 404)
    return usuario


def verificar_usuario(usuario_id: int, aprovado: bool = True) -> Usuario:
    usuario = _usuario(usuario_id)
    usuario.verificado = aprovado
    usuario.verificacao_solicitada_em = None
    if aprovado:
        notificar(usuario, "perfil_verificado", "Perfil verificado!",
                  "A administração conferiu sua matrícula. Agora seu perfil mostra o selo de verificado.")
    db.session.commit()
    return usuario


def remover_foto_usuario(usuario_id: int) -> Usuario:
    """Moderacao: tira uma foto de perfil inadequada e avisa o aluno."""
    from caronauvv.auth.foto import remover_foto

    usuario = _usuario(usuario_id)
    if not usuario.foto_url:
        raise ApiError("Este usuário não tem foto de perfil.")
    notificar(usuario, "seguranca_conta", "Foto de perfil removida",
              "A administração removeu sua foto de perfil. Envie uma foto em que apareça o seu rosto.")
    return remover_foto(usuario)


def resetar_dois_fatores(usuario_id: int) -> Usuario:
    """Aluno ficou sem o celular e sem os codigos de reserva: desliga o autenticador da conta."""
    from caronauvv.auth.dois_fatores import resetar_pelo_admin

    return resetar_pelo_admin(_usuario(usuario_id))


def suspender_usuario(usuario_id: int, admin: Usuario, ativo: bool) -> Usuario:
    usuario = _usuario(usuario_id)
    if usuario.id == admin.id:
        raise ApiError("Você não pode suspender a própria conta.")
    usuario.is_active = ativo
    if not ativo:
        # Caronas futuras do usuario suspenso sao canceladas e os passageiros avisados
        for carona in usuario.caronas_oferecidas:
            if carona.status in ("ativa", "lotada"):
                carona.status = "cancelada"
                carona.cancelada_em = datetime.now()
                for s in carona.solicitacoes:
                    if s.status in ("pendente", "aceita"):
                        s.status = "cancelada"
                        notificar(s.passageiro, "carona_cancelada", "Carona cancelada",
                                  "A carona foi cancelada pela administração. Busque outra opção.", carona)
    db.session.commit()
    return usuario


# ==========================================================
# DENUNCIAS
# ==========================================================
def listar_denuncias(status: str | None = None) -> list[Denuncia]:
    consulta = db.select(Denuncia).order_by(Denuncia.created_at.desc())
    if status:
        consulta = consulta.where(Denuncia.status == status)
    return list(db.session.scalars(consulta))


def analisar_denuncia(denuncia_id: int, admin: Usuario, status: str,
                      resolucao: str | None, suspender: bool) -> Denuncia:
    denuncia = db.session.get(Denuncia, denuncia_id)
    if denuncia is None:
        raise ApiError("Denúncia não encontrada.", 404)
    if status not in STATUS_DENUNCIA:
        raise ApiError(f"status deve ser um de: {', '.join(STATUS_DENUNCIA)}.")
    if status == "encerrada" and not resolucao:
        raise ApiError("Escreva a resolução para encerrar a denúncia.")
    denuncia.status = status
    denuncia.analisada_por_id = admin.id
    denuncia.resolucao = resolucao
    denuncia.encerrada_em = datetime.now() if status == "encerrada" else None
    if suspender:
        suspender_usuario(denuncia.denunciado_id, admin, ativo=False)
    db.session.commit()
    return denuncia


# ==========================================================
# ALERTAS DE SEGURANCA
# ==========================================================
def listar_alertas() -> list[Alerta]:
    return list(db.session.scalars(
        db.select(Alerta).order_by((Alerta.status == "resolvido"), Alerta.created_at.desc()).limit(50)
    ))


def resolver_alerta(alerta_id: int) -> Alerta:
    alerta = db.session.get(Alerta, alerta_id)
    if alerta is None:
        raise ApiError("Alerta não encontrado.", 404)
    alerta.status = "resolvido"
    alerta.resolvido_em = datetime.now()
    db.session.commit()
    return alerta


# ==========================================================
# CONFIGURACOES ("Regras e precos")
# ==========================================================
def listar_configuracoes() -> list[Configuracao]:
    return list(db.session.scalars(db.select(Configuracao).order_by(Configuracao.chave)))


def atualizar_configuracoes(valores: dict) -> list[Configuracao]:
    for chave, valor in valores.items():
        if chave not in Configuracao.PADROES:
            raise ApiError(f"Configuração desconhecida: {chave}.")
        try:
            numero = float(str(valor).replace(",", "."))
        except ValueError:
            raise ApiError(f"{chave}: precisa ser um número.")
        if numero < 0:
            raise ApiError(f"{chave}: não pode ser negativo.")
        config = db.session.get(Configuracao, chave)
        if config is None:
            config = Configuracao(chave=chave, descricao=Configuracao.PADROES[chave][1])
            db.session.add(config)
        config.valor = str(valor).replace(",", ".")
    db.session.commit()
    return listar_configuracoes()


# ==========================================================
# BANCO DE DADOS AO VIVO (para apresentar o modelo)
# Le a estrutura direto dos modelos do SQLAlchemy: tabelas, colunas,
# chaves e quantas linhas cada tabela tem agora.
# ==========================================================
def estrutura_do_banco() -> dict:
    tabelas = []
    for tabela in db.metadata.sorted_tables:
        colunas = []
        for coluna in tabela.columns:
            colunas.append({
                "nome": coluna.name,
                "tipo": str(coluna.type).split("(")[0],
                "pk": coluna.primary_key,
                "fk": next((f"{fk.column.table.name}.{fk.column.name}" for fk in coluna.foreign_keys), None),
                "obrigatorio": not coluna.nullable,
                "unico": bool(coluna.unique),
            })
        tabelas.append({
            "nome": tabela.name,
            "linhas": db.session.scalar(db.select(db.func.count()).select_from(tabela)),
            "colunas": colunas,
        })
    motor = inspect(db.engine)
    return {
        "banco": db.engine.dialect.name,
        "versao_migracao": _versao_migracao(motor),
        "tabelas": tabelas,
    }


def _versao_migracao(motor) -> str | None:
    if "alembic_version" not in motor.get_table_names():
        return None
    return db.session.scalar(db.text("SELECT version_num FROM alembic_version"))
