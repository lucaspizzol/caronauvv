import pytest

from caronauvv.auth.models import Usuario
from caronauvv.ext.db import db


DADOS_KAUA = {
    "matricula": "202416377",
    "email": "Kaua@uvv.br",
    "nome": "Kaua Araujo",
    "telefone": "27999990000",
    "bairro": "Itapua",
    "curso": "Ciencia da Computacao",
    "senha": "123456",
}


def cadastrar(client, **extra):
    return client.post("/api/auth/cadastro", json={**DADOS_KAUA, **extra})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token(client):
    return cadastrar(client).get_json()["token"]


# ==========================================================
# CADASTRO
# ==========================================================
def test_cadastro_retorna_usuario_e_token(client):
    resp = cadastrar(client)
    assert resp.status_code == 201
    corpo = resp.get_json()
    assert corpo["token"]
    assert corpo["usuario"]["email"] == "kaua@uvv.br"  # normaliza para minusculas
    assert "senha_hash" not in corpo["usuario"]
    assert db.session.scalar(db.select(Usuario)).check_senha("123456")


def test_cadastro_exige_campos_obrigatorios(client):
    resp = client.post("/api/auth/cadastro", json={"nome": "Ana"})
    assert resp.status_code == 400
    assert "matricula" in resp.get_json()["error"]


def test_cadastro_senha_curta(client):
    resp = cadastrar(client, senha="123")
    assert resp.status_code == 400


@pytest.mark.parametrize("campo", ["matricula", "email"])
def test_cadastro_duplicado(client, campo):
    cadastrar(client)
    outro = {"matricula": "999", "email": "outro@uvv.br", campo: DADOS_KAUA[campo]}
    resp = cadastrar(client, **outro)
    assert resp.status_code == 409


# ==========================================================
# LOGIN
# ==========================================================
@pytest.mark.parametrize("login", ["kaua@uvv.br", "KAUA@uvv.br", "202416377"])
def test_login_por_email_ou_matricula(client, login):
    cadastrar(client)
    resp = client.post("/api/auth/login", json={"login": login, "senha": "123456"})
    assert resp.status_code == 200
    assert resp.get_json()["token"]


def test_login_senha_errada(client):
    cadastrar(client)
    resp = client.post("/api/auth/login", json={"login": "202416377", "senha": "errada"})
    assert resp.status_code == 401


def test_login_conta_desativada(client):
    cadastrar(client)
    db.session.scalar(db.select(Usuario)).is_active = False
    db.session.commit()
    resp = client.post("/api/auth/login", json={"login": "202416377", "senha": "123456"})
    assert resp.status_code == 403


# ==========================================================
# ROTAS PROTEGIDAS
# ==========================================================
def test_me_sem_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_token_invalido(client):
    assert client.get("/api/auth/me", headers=auth_header("abc")).status_code == 401


def test_me_token_expirado(app, client, token):
    app.config["TOKEN_MAX_AGE"] = -1
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401


def test_me_retorna_perfil_completo(client, token):
    resp = client.get("/api/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["telefone"] == "27999990000"


def test_logout(client, token):
    assert client.post("/api/auth/logout", headers=auth_header(token)).status_code == 200


# ==========================================================
# PERFIL
# ==========================================================
def test_editar_perfil(client, token):
    resp = client.put("/api/auth/me", headers=auth_header(token),
                      json={"bairro": "Praia da Costa", "chave_pix": "kaua@uvv.br",
                            "matricula": "000"})  # matricula nao e editavel
    usuario = resp.get_json()["usuario"]
    assert resp.status_code == 200
    assert usuario["bairro"] == "Praia da Costa"
    assert usuario["chave_pix"] == "kaua@uvv.br"
    assert usuario["matricula"] == "202416377"


def test_editar_perfil_campo_obrigatorio_vazio(client, token):
    resp = client.put("/api/auth/me", headers=auth_header(token), json={"telefone": " "})
    assert resp.status_code == 400


def test_trocar_senha(client, token):
    resp = client.put("/api/auth/me", headers=auth_header(token),
                      json={"senha_atual": "errada", "nova_senha": "nova123"})
    assert resp.status_code == 403

    resp = client.put("/api/auth/me", headers=auth_header(token),
                      json={"senha_atual": "123456", "nova_senha": "nova123"})
    assert resp.status_code == 200
    login = client.post("/api/auth/login", json={"login": "202416377", "senha": "nova123"})
    assert login.status_code == 200


# ==========================================================
# DADOS PUBLICOS (telefone so aparece apos solicitacao aceita)
# ==========================================================
def test_to_dict_publico_esconde_contato(client):
    cadastrar(client)
    publico = db.session.scalar(db.select(Usuario)).to_dict()
    assert not {"telefone", "email", "chave_pix", "matricula"} & publico.keys()
