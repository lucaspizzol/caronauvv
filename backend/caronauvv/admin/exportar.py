"""
EXPORTAR DADOS (CSV)
Relatorios de usuarios, avaliacoes e viagens para abrir no Excel ou no
Google Planilhas. Formato brasileiro: separador ";", virgula decimal,
datas dd/mm/aaaa e UTF-8 com BOM (o Excel reconhece os acentos).

Seguranca:
- so dados necessarios para gestao (sem telefone, chave Pix, senha ou documento);
- protecao contra "injecao de formula": texto que comeca com = + - @ ganha um
  apostrofo na frente, assim o Excel nao executa nada que um aluno escreveu.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Callable, Iterable

from caronauvv.auth.models import Usuario
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.caronas.models import Carona, Solicitacao
from caronauvv.errors import ApiError
from caronauvv.ext.db import db

PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")
STATUS_CARONA = {"ativa": "Ativa", "lotada": "Lotada", "em_andamento": "Em andamento",
                 "concluida": "Concluída", "cancelada": "Cancelada"}


def _trecho(c: Carona) -> str:
    """Ida: bairro -> UVV; volta: UVV -> bairro (igual aos cartoes do app)."""
    return f"{c.bairro_origem} → {c.destino}" if c.sentido == "ida" else f"{c.destino} → {c.bairro_origem}"


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, (float, Decimal)):
        return f"{valor:.2f}".replace(".", ",")
    texto = str(valor).replace("\r\n", " ").replace("\n", " ")
    return "'" + texto if texto.startswith(PERIGOSOS) else texto


def _csv(cabecalho: list[str], linhas: Iterable[list]) -> tuple[str, int]:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(cabecalho)
    total = 0
    for linha in linhas:
        escritor.writerow([_celula(v) for v in linha])
        total += 1
    return "﻿" + saida.getvalue(), total


# ==========================================================
# USUARIOS
# ==========================================================
def _usuarios() -> tuple[str, int]:
    medias = {uid: (media, n) for uid, media, n in db.session.execute(
        db.select(Avaliacao.avaliado_id, db.func.avg(Avaliacao.nota), db.func.count()).group_by(Avaliacao.avaliado_id))}
    oferecidas = dict(db.session.execute(
        db.select(Carona.motorista_id, db.func.count()).group_by(Carona.motorista_id)).all())
    como_passageiro = dict(db.session.execute(
        db.select(Solicitacao.passageiro_id, db.func.count())
        .where(Solicitacao.status == "aceita", Solicitacao.faltou.is_(False))
        .group_by(Solicitacao.passageiro_id)).all())

    def linhas():
        for u in db.session.scalars(db.select(Usuario).order_by(Usuario.nome)):
            media, n = medias.get(u.id, (None, 0))
            yield [
                u.id, u.nome, u.email, u.matricula, u.curso, u.bairro,
                u.is_admin, u.verificado, u.documento_aprovado("identidade"), u.documento_aprovado("cnh"),
                "Ativa" if u.is_active else "Suspensa", u.suspenso_motivo,
                float(media) if media is not None else None, n,
                oferecidas.get(u.id, 0), como_passageiro.get(u.id, 0),
                u.created_at, u.ultimo_login_em,
            ]

    return _csv(
        ["ID", "Nome", "E-mail", "Matrícula", "Curso", "Bairro", "Administrador", "Perfil verificado",
         "Identidade verificada", "CNH verificada", "Conta", "Motivo da suspensão", "Média recebida",
         "Avaliações recebidas", "Caronas oferecidas", "Viagens como passageiro", "Cadastro", "Último acesso"],
        linhas(),
    )


# ==========================================================
# AVALIACOES
# ==========================================================
def _avaliacoes() -> tuple[str, int]:
    def linhas():
        for a in db.session.scalars(db.select(Avaliacao).order_by(Avaliacao.created_at.desc())):
            carona = a.solicitacao.carona
            papel = "Motorista" if a.avaliado_id == carona.motorista_id else "Passageiro"
            yield [
                a.id, a.created_at, carona.id, _trecho(carona), carona.data_hora_saida, a.avaliador.nome, a.avaliado.nome, papel, a.nota, a.comentario,
                ", ".join(t.tag for t in a.tags),
            ]

    return _csv(["ID", "Data", "Carona", "Trecho", "Saída da carona", "Quem avaliou", "Avaliado(a)",
                 "Papel do avaliado", "Nota", "Comentário", "Etiquetas"], linhas())


# ==========================================================
# VIAGENS (caronas)
# ==========================================================
def _viagens() -> tuple[str, int]:
    def linhas():
        for c in db.session.scalars(db.select(Carona).order_by(Carona.data_hora_saida.desc())):
            aceitas = [s for s in c.solicitacoes if s.status == "aceita"]
            faltas = sum(1 for s in aceitas if s.faltou)
            duracao = (round((c.concluida_em - c.iniciada_em).total_seconds() / 60)
                       if c.iniciada_em and c.concluida_em else None)
            yield [
                c.id, c.data_hora_saida, "Ida para a UVV" if c.sentido == "ida" else "Volta da UVV",
                _trecho(c), c.motorista.nome,
                c.veiculo.modelo if c.veiculo else None, c.veiculo.placa if c.veiculo else None,
                STATUS_CARONA.get(c.status, c.status), c.vagas, len(aceitas) - faltas, faltas,
                c.distancia_km, c.valor_por_passageiro, c.iniciada_em, c.concluida_em, duracao,
            ]

    return _csv(["Carona", "Saída", "Sentido", "Trecho", "Motorista", "Carro", "Placa", "Situação",
                 "Vagas", "Passageiros que viajaram", "Faltas", "Distância (km)", "Valor por passageiro (R$)",
                 "Iniciada em", "Concluída em", "Duração (min)"], linhas())


RELATORIOS: dict[str, tuple[str, Callable[[], tuple[str, int]]]] = {
    "usuarios": ("Usuários", _usuarios),
    "avaliacoes": ("Avaliações", _avaliacoes),
    "viagens": ("Viagens", _viagens),
}


def exportar(tipo: str) -> tuple[str, str, int]:
    """Devolve (nome legivel, conteudo CSV, quantidade de linhas)."""
    if tipo not in RELATORIOS:
        raise ApiError(f"Relatório desconhecido. Use um de: {', '.join(RELATORIOS)}.", 404)
    nome, gerar = RELATORIOS[tipo]
    conteudo, total = gerar()
    return nome, conteudo, total
