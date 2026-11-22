"""
Validacao dos formularios no servidor (Pydantic) e confianca no cadastro:
e-mail institucional, codigo de verificacao, protecao do login.
"""
import pytest

from caronauvv.auth.models import Usuario
from caronauvv.ext.db import db

DADOS = {
    "matricula": "202416377", "email": "kaua@uvv.br", "nome": "Kaua Araujo",
    "telefone": "(27) 99999-0000", "bairro": "Itapua", "senha": "123456",
}


def cadastrar(client, **extra):
    return client.post("/api/auth/cadastro", json={**DADOS, **extra})


def headers(resp):
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


# ==========================================================
# FORMULARIO DE CADASTRO
# ==========================================================
@pytest.mark.parametrize("email", ["ana@gmail.com", "ana@uvv.com", "ana@fakeuvv.br"])
def test_so_aceita_email_institucional(client, email):
    resp = cadastrar(client, email=email)
    assert resp.status_code == 400
    assert "institucional" in resp.get_json()["campos"]["email"]


def test_aceita_subdominio_da_uvv(client):
    assert cadastrar(client, email="kaua@aluno.uvv.br").status_code == 201


def test_erros_voltam_por_campo(client):
    resp = client.post("/api/auth/cadastro", json={"email": "x", "telefone": "123", "matricula": "ab"})
    corpo = resp.get_json()
    assert resp.status_code == 400
    assert corpo["error"].startswith("Campos obrigatórios:")
    assert {"nome", "bairro", "senha"} <= set(corpo["campos"])
    assert corpo["campos"]["matricula"] == "A matrícula tem de 5 a 12 números."
    assert "DDD" in corpo["campos"]["telefone"]


def test_telefone_e_guardado_so_com_numeros(client):
    corpo = cadastrar(client).get_json()
    assert corpo["usuario"]["telefone"] == "27999990000"


def test_textos_sao_aparados(client):
    corpo = cadastrar(client, nome="   Kaua Araujo  ", curso="   ").get_json()
    assert corpo["usuario"]["nome"] == "Kaua Araujo"
    assert corpo["usuario"]["curso"] is None


def test_json_invalido(client):
    resp = client.post("/api/auth/cadastro", data="nao e json", content_type="application/json")
    assert resp.status_code == 400


# ==========================================================
# VERIFICACAO DO E-MAIL UVV
# ==========================================================
def test_cadastro_comeca_sem_email_confirmado(client):
    corpo = cadastrar(client).get_json()
    assert corpo["usuario"]["email_verificado"] is False
    assert len(corpo["codigo_dev"]) == 6


def test_codigo_nao_fica_salvo_em_texto(client):
    codigo = cadastrar(client).get_json()["codigo_dev"]
    usuario = db.session.scalar(db.select(Usuario))
    assert codigo not in usuario.codigo_verificacao_hash


def test_confirma_email_com_codigo(client):
    resp = cadastrar(client)
    codigo = resp.get_json()["codigo_dev"]
    confirma = client.post("/api/auth/verificar-email", json={"codigo": codigo}, headers=headers(resp))
    assert confirma.status_code == 200
    assert confirma.get_json()["usuario"]["email_verificado"] is True


def test_codigo_errado_e_limite_de_tentativas(client):
    resp = cadastrar(client)
    h = headers(resp)
    for _ in range(5):
        errado = client.post("/api/auth/verificar-email", json={"codigo": "000000"}, headers=h)
        assert errado.status_code == 400
    # depois de 5 erros nem o codigo certo passa: precisa pedir outro
    certo = client.post("/api/auth/verificar-email", json={"codigo": resp.get_json()["codigo_dev"]}, headers=h)
    assert certo.status_code == 429


def test_reenviar_codigo_invalida_o_anterior(client):
    resp = cadastrar(client)
    h = headers(resp)
    antigo = resp.get_json()["codigo_dev"]
    novo = client.post("/api/auth/reenviar-codigo", headers=h).get_json()["codigo_dev"]
    if antigo != novo:
        assert client.post("/api/auth/verificar-email", json={"codigo": antigo}, headers=h).status_code == 400
    assert client.post("/api/auth/verificar-email", json={"codigo": novo}, headers=h).status_code == 200


def test_codigo_precisa_ter_6_numeros(client):
    resp = cadastrar(client)
    r = client.post("/api/auth/verificar-email", json={"codigo": "12"}, headers=headers(resp))
    assert r.status_code == 400
    assert r.get_json()["campos"]["codigo"] == "O código tem 6 números."


def test_sem_email_confirmado_nao_oferece_nem_pede_carona(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1", "Kaua")
    carona = nova_carona(h_motorista)
    _, h_novo = novo_aluno("2", "Ana", confirmar=False)

    pedir = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_novo)
    assert pedir.status_code == 403
    assert "Confirme seu e-mail" in pedir.get_json()["error"]

    oferecer = client.post("/api/caronas", json={
        "bairro_origem": "Gloria", "endereco_origem": "Rua A", "vagas": 2,
        "data_hora_saida": carona["data_hora_saida"],
    }, headers=h_novo)
    assert oferecer.status_code == 403


def test_pedir_selo_de_perfil_verificado(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    resp = client.post("/api/auth/solicitar-verificacao", headers=h)
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["verificacao_solicitada_em"]


# ==========================================================
# LOGIN: protecao contra forca bruta
# ==========================================================
def test_login_bloqueia_depois_de_5_erros(client):
    cadastrar(client)
    for _ in range(5):
        assert client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "errada"}).status_code == 401
    bloqueado = client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "123456"})
    assert bloqueado.status_code == 429


def test_login_certo_zera_as_tentativas(client):
    cadastrar(client)
    for _ in range(4):
        client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "errada"})
    assert client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "123456"}).status_code == 200
    assert client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "errada"}).status_code == 401


# ==========================================================
# PERFIL: preferencias de viagem e bio
# ==========================================================
def test_salva_preferencias_e_bio(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    resp = client.put("/api/auth/me", json={
        "bio": "Saio pontualmente", "pref_conversa": "quieto", "pref_animais": True,
    }, headers=h)
    u = resp.get_json()["usuario"]
    assert resp.status_code == 200
    assert u["bio"] == "Saio pontualmente"
    assert u["preferencias"] == {"conversa": "quieto", "musica": True, "animais": True, "fumar": False}


def test_preferencia_invalida(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    resp = client.put("/api/auth/me", json={"pref_conversa": "gritando"}, headers=h)
    assert resp.status_code == 400
    assert "pref_conversa" in resp.get_json()["campos"]


def test_bio_tem_limite(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    resp = client.put("/api/auth/me", json={"bio": "x" * 301}, headers=h)
    assert resp.get_json()["campos"]["bio"] == "Máximo de 300 caracteres."
