"""Verificacao de documentos: envio, analise pelo admin, imagem apagada (LGPD), selos e regras opcionais."""
import io
from datetime import date, timedelta

from caronauvv.admin.models import Configuracao
from caronauvv.auth.models import Documento
from caronauvv.ext.db import db
from tests.test_foto_perfil import JPEG, png

VALIDADE = (date.today() + timedelta(days=700)).isoformat()


def enviar(client, headers, tipo="identidade", dados=JPEG, validade=None):
    corpo = {"documento": (io.BytesIO(dados), "doc.jpg")}
    if validade:
        corpo["validade"] = validade
    return client.put(f"/api/auth/me/documentos/{tipo}", data=corpo, headers=headers,
                      content_type="multipart/form-data")


def situacao(client, headers) -> dict:
    lista = client.get("/api/auth/me/documentos", headers=headers).get_json()["documentos"]
    return {d["tipo"]: d for d in lista}


def pendentes(client, admin):
    return client.get("/api/admin/documentos", headers=admin[1]).get_json()["documentos"]


def analisar(client, admin, doc_id, aprovado=True, motivo=None):
    return client.post(f"/api/admin/documentos/{doc_id}/analisar",
                       json={"aprovado": aprovado, "motivo": motivo}, headers=admin[1])


# ==========================================================
# ALUNO ENVIA
# ==========================================================
def test_situacao_inicial(client, novo_aluno):
    _, h = novo_aluno(1)
    docs = situacao(client, h)
    assert docs["identidade"]["status"] == "nao_enviado"
    assert docs["cnh"]["status"] == "nao_enviado"


def test_envia_identidade_e_fica_pendente(client, novo_aluno, admin):
    _, h = novo_aluno(1)
    resp = enviar(client, h)
    assert resp.status_code == 200, resp.get_json()
    assert situacao(client, h)["identidade"]["status"] == "pendente"
    assert situacao(client, h)["identidade"]["tem_imagem"] is True
    # a administracao e avisada
    avisos = client.get("/api/notificacoes", headers=admin[1]).get_json()["notificacoes"]
    assert any(n["tipo"] == "documento" for n in avisos)


def test_cnh_precisa_de_validade_no_futuro(client, novo_aluno):
    _, h = novo_aluno(1)
    sem = enviar(client, h, "cnh")
    assert sem.status_code == 400 and "validade" in sem.get_json()["campos"]
    vencida = enviar(client, h, "cnh", validade=(date.today() - timedelta(days=1)).isoformat())
    assert vencida.status_code == 400 and "vencida" in vencida.get_json()["error"]
    assert enviar(client, h, "cnh", validade=VALIDADE).status_code == 200
    assert situacao(client, h)["cnh"]["validade"] == VALIDADE


def test_arquivo_que_nao_e_imagem_e_recusado(client, novo_aluno):
    _, h = novo_aluno(1)
    assert enviar(client, h, dados=b"%PDF-1.7 nao e foto").status_code == 415
    assert enviar(client, h, dados=b"").status_code == 400
    assert enviar(client, h, dados=png(3000, 100)).status_code == 413     # lado grande demais


def test_tipo_invalido(client, novo_aluno):
    _, h = novo_aluno(1)
    assert enviar(client, h, "passaporte").status_code == 404


# ==========================================================
# ADMIN ANALISA
# ==========================================================
def test_admin_ve_a_imagem_e_aprova_e_a_imagem_some(client, novo_aluno, admin):
    usuario, h = novo_aluno(1)
    enviar(client, h)
    doc = pendentes(client, admin)[0]
    assert doc["usuario"]["id"] == usuario["id"]

    imagem = client.get(f"/api/admin/documentos/{doc['id']}/imagem", headers=admin[1])
    assert imagem.status_code == 200 and imagem.data == JPEG
    assert imagem.headers["Cache-Control"] == "no-store"

    assert analisar(client, admin, doc["id"]).status_code == 200
    # LGPD: depois da analise a imagem e apagada e fica so o resultado
    assert db.session.get(Documento, doc["id"]).dados is None
    assert client.get(f"/api/admin/documentos/{doc['id']}/imagem", headers=admin[1]).status_code == 410
    assert situacao(client, h)["identidade"]["status"] == "aprovado"
    assert pendentes(client, admin) == []


def test_recusa_exige_motivo_e_aluno_pode_reenviar(client, novo_aluno, admin):
    _, h = novo_aluno(1)
    enviar(client, h)
    doc_id = pendentes(client, admin)[0]["id"]
    assert analisar(client, admin, doc_id, aprovado=False).status_code == 400
    assert analisar(client, admin, doc_id, aprovado=False, motivo="Foto desfocada.").status_code == 200
    recusado = situacao(client, h)["identidade"]
    assert recusado["status"] == "recusado" and recusado["motivo_recusa"] == "Foto desfocada."
    # nao da para analisar de novo
    assert analisar(client, admin, doc_id).status_code == 409
    # reenvio volta para a fila
    assert enviar(client, h).status_code == 200
    assert situacao(client, h)["identidade"]["status"] == "pendente"


def test_aprovado_nao_reenvia(client, novo_aluno, admin):
    _, h = novo_aluno(1)
    enviar(client, h)
    analisar(client, admin, pendentes(client, admin)[0]["id"])
    assert enviar(client, h).status_code == 409


def test_aluno_comum_nao_ve_documento_dos_outros(client, novo_aluno):
    _, h1 = novo_aluno(1)
    _, h2 = novo_aluno(2)
    enviar(client, h1)
    doc = db.session.scalar(db.select(Documento))
    assert client.get("/api/admin/documentos", headers=h2).status_code == 403
    assert client.get(f"/api/admin/documentos/{doc.id}/imagem", headers=h2).status_code == 403


# ==========================================================
# SELOS E REGRAS
# ==========================================================
def test_selos_aparecem_no_perfil_publico(client, novo_aluno, admin):
    usuario, h = novo_aluno(1)
    _, outro = novo_aluno(2)
    enviar(client, h)
    enviar(client, h, "cnh", validade=VALIDADE)
    for doc in pendentes(client, admin):
        analisar(client, admin, doc["id"])
    perfil = client.get(f"/api/usuarios/{usuario['id']}", headers=outro).get_json()["usuario"]
    assert perfil["identidade_verificada"] is True and perfil["cnh_verificada"] is True
    codigos = {s["codigo"] for s in perfil["reputacao"]["selos"]}
    assert {"identidade_verificada", "cnh_verificada"} <= codigos


def test_cnh_vencida_perde_o_selo(client, novo_aluno, admin):
    usuario, h = novo_aluno(1)
    enviar(client, h, "cnh", validade=VALIDADE)
    analisar(client, admin, pendentes(client, admin)[0]["id"])
    doc = db.session.scalar(db.select(Documento))
    doc.validade = date.today() - timedelta(days=1)
    db.session.commit()
    assert client.get("/api/auth/me", headers=h).get_json()["usuario"]["cnh_verificada"] is False


def _ligar(chave):
    db.session.add(Configuracao(chave=chave, valor="1"))
    db.session.commit()


def test_regra_exigir_cnh_para_oferecer(client, novo_aluno, nova_carona, admin):
    _, h = novo_aluno(1)
    _ligar("exigir_cnh_motorista")
    dados = {"bairro_origem": "Itapua", "endereco_origem": "Rua A", "vagas": 2, "data_hora_saida": "2099-01-01T10:00"}
    resp = client.post("/api/caronas", json=dados, headers=h)
    assert resp.status_code == 403 and "CNH" in resp.get_json()["error"]
    enviar(client, h, "cnh", validade=VALIDADE)
    analisar(client, admin, pendentes(client, admin)[0]["id"])
    assert client.post("/api/caronas", json=dados, headers=h).status_code == 201


def test_regra_exigir_identidade_para_pedir_vaga(client, novo_aluno, nova_carona, admin):
    _, motorista = novo_aluno(1)
    _, passageiro = novo_aluno(2)
    carona = nova_carona(motorista)
    _ligar("exigir_identidade_passageiro")
    resp = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=passageiro)
    assert resp.status_code == 403 and "identidade" in resp.get_json()["error"]
    enviar(client, passageiro)
    analisar(client, admin, pendentes(client, admin)[0]["id"])
    assert client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=passageiro).status_code == 201


def test_resumo_do_admin_conta_documentos_pendentes(client, novo_aluno, admin):
    _, h = novo_aluno(1)
    enviar(client, h)
    resumo = client.get("/api/admin/resumo", headers=admin[1]).get_json()["resumo"]
    assert resumo["usuarios"]["documentos_pendentes"] == 1
