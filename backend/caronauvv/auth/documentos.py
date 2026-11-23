"""
VERIFICACAO DE DOCUMENTOS (identidade e CNH)

1. O aluno envia a foto do documento pelo perfil (PUT /api/auth/me/documentos/<tipo>).
   O navegador ja reduz a imagem; o servidor confere o formato pelo conteudo do
   arquivo (mesma checagem da foto de perfil) e o tamanho.
2. A administracao ve a imagem no painel e aprova ou recusa (com o motivo).
3. Depois da analise a imagem e APAGADA: fica so o resultado (aprovado/recusado,
   validade da CNH). Documento e dado pessoal sensivel; guardar so o necessario
   e o principio da minimizacao de dados da LGPD.

Aprovados viram selos ("Identidade verificada", "CNH verificada") no perfil e no
cartao da carona. O painel pode exigir CNH de quem oferece carona e identidade
de quem pede vaga (configuracoes exigir_cnh_motorista / exigir_identidade_passageiro).
"""
from datetime import date, datetime

from flask import current_app

from caronauvv.admin.models import Configuracao
from caronauvv.errors import ApiError
from caronauvv.ext.db import db
from caronauvv.notificacoes.services import notificar, notificar_admins

from .foto import FORMATOS, identificar_imagem
from .models import TIPOS_DOCUMENTO, Documento, Usuario

NOMES = {"identidade": "identidade", "cnh": "CNH"}


def _tipo(tipo: str) -> str:
    if tipo not in TIPOS_DOCUMENTO:
        raise ApiError("Tipo de documento inválido (use identidade ou cnh).", 404)
    return tipo


def _validade(texto: str | None, tipo: str) -> date | None:
    if tipo != "cnh":
        return None
    if not texto:
        raise ApiError("Informe a validade da CNH.", campos={"validade": "Informe a validade da CNH."})
    try:
        validade = date.fromisoformat(texto)
    except ValueError:
        raise ApiError("Data de validade inválida.", campos={"validade": "Use uma data válida."})
    if validade < date.today():
        raise ApiError("Esta CNH está vencida.", campos={"validade": "A CNH está vencida."})
    return validade


def enviar_documento(usuario: Usuario, tipo: str, dados: bytes, validade: str | None = None) -> Documento:
    tipo = _tipo(tipo)
    cfg = current_app.config
    if not dados:
        raise ApiError("Escolha a foto do documento.", campos={"documento": "Escolha a foto do documento."})
    if len(dados) > cfg["DOCUMENTO_MAX_KB"] * 1024:
        raise ApiError(f"A imagem passou de {cfg['DOCUMENTO_MAX_KB']} KB. Envie uma foto menor.", 413)
    imagem = identificar_imagem(dados)
    if imagem is None:
        raise ApiError(f"Arquivo inválido: envie uma foto do documento em {FORMATOS}.", 415)
    mime, largura, altura = imagem
    if max(largura, altura) > cfg["DOCUMENTO_MAX_LADO_PX"]:
        raise ApiError(f"A imagem pode ter no máximo {cfg['DOCUMENTO_MAX_LADO_PX']} pixels de lado.", 413)
    data_validade = _validade(validade, tipo)

    doc = usuario.documento(tipo)
    if doc is not None and doc.status == "aprovado" and not doc.vencido:
        raise ApiError(f"Sua {NOMES[tipo]} já está verificada.", 409)
    if doc is None:
        doc = Documento(usuario=usuario, tipo=tipo)
        db.session.add(doc)

    # Reenvio: volta para a fila da administracao
    doc.status = "pendente"
    doc.validade = data_validade
    doc.mime, doc.tamanho, doc.dados = mime, len(dados), dados
    doc.motivo_recusa = None
    doc.enviado_em = datetime.now()
    doc.analisado_em = None
    doc.analisado_por_id = None
    notificar_admins("documento", "Documento para conferir",
                     f"{usuario.nome} enviou a {NOMES[tipo]} para verificação.")
    db.session.commit()
    return doc


def documentos_do_usuario(usuario: Usuario) -> list[dict]:
    """Situacao de cada tipo de documento (inclusive os que ainda nao foram enviados)."""
    lista = []
    for tipo in TIPOS_DOCUMENTO:
        doc = usuario.documento(tipo)
        lista.append(doc.to_dict() if doc else {"tipo": tipo, "status": "nao_enviado"})
    return lista


# ==========================================================
# ADMINISTRACAO
# ==========================================================
def listar_documentos(status: str = "pendente") -> list[Documento]:
    consulta = db.select(Documento).order_by(Documento.enviado_em)
    if status:
        consulta = consulta.where(Documento.status == status)
    return list(db.session.scalars(consulta))


def buscar_documento(documento_id: int) -> Documento:
    doc = db.session.get(Documento, documento_id)
    if doc is None:
        raise ApiError("Documento não encontrado.", 404)
    return doc


def imagem_do_documento(doc: Documento) -> tuple[bytes, str]:
    if doc.dados is None:
        raise ApiError("A imagem já foi apagada depois da análise.", 410)
    return doc.dados, doc.mime or "application/octet-stream"


def analisar_documento(doc: Documento, admin: Usuario, aprovado: bool, motivo: str | None = None) -> Documento:
    if doc.status != "pendente":
        raise ApiError("Este documento já foi analisado.", 409)
    motivo = (motivo or "").strip()
    if not aprovado and not motivo:
        raise ApiError("Diga o motivo da recusa (o aluno vê esse texto).", campos={"motivo": "Informe o motivo."})
    if aprovado and doc.vencido:
        raise ApiError("Não dá para aprovar: a CNH está vencida.")

    doc.status = "aprovado" if aprovado else "recusado"
    doc.motivo_recusa = None if aprovado else motivo[:255]
    doc.analisado_em = datetime.now()
    doc.analisado_por_id = admin.id
    # LGPD: depois da analise a imagem nao e mais necessaria
    doc.dados, doc.mime, doc.tamanho = None, None, None

    from caronauvv.admin.historico import registrar_acao
    registrar_acao(admin, "aprovar_documento" if aprovado else "recusar_documento", doc.usuario,
                   NOMES[doc.tipo] + ("" if aprovado else f": {doc.motivo_recusa}"))

    nome = NOMES[doc.tipo]
    if aprovado:
        notificar(doc.usuario, "documento", f"{nome[0].upper() + nome[1:]} verificada!",
                  f"A administração conferiu sua {nome}. O selo já aparece no seu perfil.")
    else:
        notificar(doc.usuario, "documento", f"{nome[0].upper() + nome[1:]} recusada",
                  f"Motivo: {doc.motivo_recusa} Envie uma nova foto em Meu perfil.")
    db.session.commit()
    return doc


def exigir_documento(usuario: Usuario, tipo: str, config: str, acao: str) -> None:
    """Regra opcional do painel: so faz a acao quem tem o documento verificado."""
    if Configuracao.obter_int(config, 0) and not usuario.documento_aprovado(tipo):
        raise ApiError(
            f"Para {acao}, envie sua {NOMES[tipo]} em Meu perfil e aguarde a verificação da administração.", 403
        )
