"""
PAINEL DA ADMINISTRACAO
Indicadores, moderacao (denuncias, suspensao, selo de verificado),
alertas de seguranca, demanda sem oferta e configuracoes.
"""
from datetime import datetime, timedelta

from sqlalchemy import inspect

from caronauvv.auth.models import Documento, Usuario
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.caronas.models import Carona, Solicitacao
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar
from caronauvv.seguranca.models import STATUS_DENUNCIA, Alerta, Denuncia

from .historico import registrar_acao
from .models import Busca, Configuracao

KG_CO2_POR_KM = 0.12  # emissao media de um carro popular (kg de CO2 por km)


def _contar(modelo, *condicoes) -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(modelo).where(*condicoes))


# ==========================================================
# INDICADORES (KPIs)
# ==========================================================
def resumo() -> dict:
    from caronauvv.caronas.viagem import medias_das_viagens

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
        .limit(30)
    ).all()
    # So bairros de verdade (buscas antigas pela metade, como "S", ficam de fora), juntando grafias
    from caronauvv.lugares.services import achar_bairro
    demanda: dict[str, int] = {}
    for nome, qtd in sem_resultado:
        conhecido = achar_bairro(nome)
        if conhecido:
            demanda[conhecido["nome"]] = demanda.get(conhecido["nome"], 0) + qtd
    sem_resultado = sorted(demanda.items(), key=lambda par: (-par[1], par[0]))[:5]
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
            "documentos_pendentes": _contar(Documento, Documento.status == "pendente"),
        },
        "caronas": {"total": sum(por_status.values()), "por_status": por_status},
        "viagens": {
            "concluidas": len(concluidas),
            "em_andamento_agora": _contar(Carona, Carona.status == "em_andamento"),
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
            "avaliacoes_baixas_abertas": _contar(Alerta, Alerta.tipo == "avaliacao_baixa", Alerta.status != "resolvido"),
            "excluidos_automaticamente": _contar(Usuario, Usuario.suspenso_motivo.like("Exclusão automática%")),
        },
        "caronas_por_dia": caronas_por_dia(),
        "medias": medias_das_viagens(),   # tempo de viagem, atraso na saida, velocidade, tempo a bordo
        "demanda_sem_oferta": [{"bairro": b, "buscas": n} for b, n in sem_resultado],
        "bairros_com_mais_oferta": [{"bairro": b, "caronas": n} for b, n in bairros_oferta],
    }


def caronas_por_dia(dias: int = 30) -> list[dict]:
    """Grafico da visao geral: caronas por dia de saida nos ultimos `dias` dias (hoje incluido).
    Agrupa em Python para funcionar igual no SQLite e no PostgreSQL."""
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=dias - 1)
    contagem = {inicio + timedelta(days=i): {"concluidas": 0, "canceladas": 0, "outras": 0} for i in range(dias)}
    linhas = db.session.execute(
        db.select(Carona.data_hora_saida, Carona.status).where(
            Carona.data_hora_saida >= datetime.combine(inicio, datetime.min.time()),
            Carona.data_hora_saida < datetime.combine(hoje + timedelta(days=1), datetime.min.time()),
        )
    ).all()
    for saida, status in linhas:
        grupo = "concluidas" if status == "concluida" else "canceladas" if status == "cancelada" else "outras"
        contagem[saida.date()][grupo] += 1
    return [{"dia": dia.isoformat(), **valores, "total": sum(valores.values())} for dia, valores in contagem.items()]


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


def verificar_usuario(usuario_id: int, aprovado: bool = True, admin: Usuario | None = None) -> Usuario:
    usuario = _usuario(usuario_id)
    usuario.verificado = aprovado
    usuario.verificacao_solicitada_em = None
    registrar_acao(admin, "aprovar_selo" if aprovado else "recusar_selo", usuario,
                   f"Matrícula {usuario.matricula}" if usuario.matricula else None)
    if aprovado:
        notificar(usuario, "perfil_verificado", "Perfil verificado!",
                  "A administração conferiu sua matrícula. Agora seu perfil mostra o selo de verificado.")
    db.session.commit()
    return usuario


def remover_foto_usuario(usuario_id: int, admin: Usuario | None = None) -> Usuario:
    """Moderacao: tira uma foto de perfil inadequada e avisa o aluno."""
    from caronauvv.auth.foto import remover_foto

    usuario = _usuario(usuario_id)
    if not usuario.foto_url:
        raise ApiError("Este usuário não tem foto de perfil.")
    registrar_acao(admin, "remover_foto", usuario, "Foto de perfil inadequada")
    notificar(usuario, "seguranca_conta", "Foto de perfil removida",
              "A administração removeu sua foto de perfil. Envie uma foto em que apareça o seu rosto.")
    return remover_foto(usuario)


def resetar_dois_fatores(usuario_id: int, admin: Usuario | None = None) -> Usuario:
    """Aluno ficou sem o celular e sem os codigos de reserva: desliga o autenticador da conta."""
    from caronauvv.auth.dois_fatores import resetar_pelo_admin

    usuario = _usuario(usuario_id)
    registrar_acao(admin, "resetar_2fa", usuario, "Verificação em duas etapas desligada a pedido do aluno")
    return resetar_pelo_admin(usuario)


def suspender_usuario(usuario_id: int, admin: Usuario, ativo: bool) -> Usuario:
    usuario = _usuario(usuario_id)
    if usuario.id == admin.id:
        raise ApiError("Você não pode suspender a própria conta.")
    if ativo:
        if not usuario.is_active:
            registrar_acao(admin, "reativar", usuario, f"Motivo anterior: {usuario.suspenso_motivo}"
                           if usuario.suspenso_motivo else None)
        usuario.is_active = True
        usuario.suspenso_em = None
        usuario.suspenso_motivo = None
    else:
        if usuario.is_active:
            registrar_acao(admin, "suspender", usuario, "Suspenso(a) pela administração")
        # Caronas futuras e pedidos em aberto sao cancelados (passageiros e motoristas avisados)
        from caronauvv.avaliacoes.moderacao import suspender_conta
        suspender_conta(usuario, f"Suspenso(a) pela administração ({admin.nome}).")
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
    registrar_acao(admin, "encerrar_denuncia" if status == "encerrada" else "analisar_denuncia",
                   denuncia.denunciado, f"Denúncia #{denuncia.id}" + (f": {resolucao}" if resolucao else ""))
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


def resolver_alerta(alerta_id: int, admin: Usuario | None = None) -> Alerta:
    alerta = db.session.get(Alerta, alerta_id)
    if alerta is None:
        raise ApiError("Alerta não encontrado.", 404)
    if alerta.status != "resolvido":
        registrar_acao(admin, "resolver_alerta", alerta.usuario, f"Alerta #{alerta.id} ({alerta.tipo.replace('_', ' ')})")
    alerta.status = "resolvido"
    alerta.resolvido_em = datetime.now()
    db.session.commit()
    return alerta


# ==========================================================
# CONFIGURACOES ("Regras e precos")
# ==========================================================
def listar_configuracoes() -> list[Configuracao]:
    # Regra nova (ex.: preco do kWh) ainda nao gravada num banco antigo: entra com o valor padrao
    existentes = set(db.session.scalars(db.select(Configuracao.chave)))
    faltando = [c for c in Configuracao.PADROES if c not in existentes]
    for chave in faltando:
        valor, descricao = Configuracao.PADROES[chave]
        db.session.add(Configuracao(chave=chave, valor=valor, descricao=descricao))
    if faltando:
        db.session.commit()
    return list(db.session.scalars(db.select(Configuracao).order_by(Configuracao.chave)))


def atualizar_configuracoes(valores: dict, admin: Usuario | None = None) -> list[Configuracao]:
    mudancas = []
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
        novo = str(valor).replace(",", ".")
        antes = config.valor if config.valor is not None else Configuracao.PADROES[chave][0]
        if antes != novo:
            mudancas.append(f"{chave}: {antes} → {novo}")
        config.valor = novo
    if mudancas:
        registrar_acao(admin, "alterar_regras", None, "; ".join(mudancas))
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
