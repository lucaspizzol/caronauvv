from datetime import datetime, timedelta

import pytest

from caronauvv import create_app
from caronauvv.config import TestConfig
from caronauvv.ext.db import db


@pytest.fixture
def app():
    from caronauvv.limite import zerar
    from caronauvv.lugares.externos import limpar_cache

    zerar()          # contadores do limite de requisicoes comecam do zero em cada teste
    limpar_cache()
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def novo_aluno(client):
    """
    Cadastra um aluno pela API, confirma o e-mail UVV com o codigo
    e devolve (usuario_dict, headers com o token).
    Use confirmar=False para testar o aluno que ainda nao confirmou o e-mail.
    """

    def _cadastrar(matricula, nome="Aluno", bairro="Itapua", confirmar=True):
        matricula = str(matricula).zfill(9)  # matricula da UVV tem 9 numeros ("1" -> "000000001")
        resp = client.post("/api/auth/cadastro", json={
            "matricula": matricula, "email": f"{matricula}@uvv.br", "nome": nome,
            "telefone": "27999990000", "bairro": bairro, "senha": "123456",
        })
        corpo = resp.get_json()
        assert resp.status_code == 201, corpo
        headers = {"Authorization": f"Bearer {corpo['token']}"}
        if confirmar:
            resp = client.post("/api/auth/verificar-email", json={"codigo": corpo["codigo_dev"]}, headers=headers)
            assert resp.status_code == 200, resp.get_json()
            corpo["usuario"] = resp.get_json()["usuario"]
        return corpo["usuario"], headers

    return _cadastrar


@pytest.fixture
def nova_carona(client):
    """Publica uma carona (saida daqui a 4 h, 2 vagas) e devolve o dict da API."""

    def _publicar(headers, **extra):
        dados = {
            "bairro_origem": "Itapua",
            "endereco_origem": "Rua Itaunas, 120",
            "data_hora_saida": (datetime.now() + timedelta(hours=4)).isoformat(timespec="minutes"),
            "vagas": 2,
            **extra,
        }
        resp = client.post("/api/caronas", json=dados, headers=headers)
        assert resp.status_code == 201, resp.get_json()
        return resp.get_json()["carona"]

    return _publicar


@pytest.fixture
def admin(client, novo_aluno):
    """Aluno com permissao de administrador (painel /admin)."""
    from caronauvv.auth.models import Usuario

    usuario, headers = novo_aluno("900000001", "Admin")
    db.session.get(Usuario, usuario["id"]).is_admin = True
    db.session.commit()
    return usuario, headers


@pytest.fixture
def viagem(client, novo_aluno, nova_carona):
    """
    Carona que sai daqui a 10 min (ja pode ser iniciada) com um passageiro aceito.
    Devolve um dict com motorista/passageiro (headers), carona, solicitacao e pin.
    """
    motorista, h_motorista = novo_aluno("100000001", "Kaua Araujo")
    passageiro, h_passageiro = novo_aluno("100000002", "Ana Souza")
    carona = nova_carona(
        h_motorista, valor_por_passageiro=1.5,
        data_hora_saida=(datetime.now() + timedelta(minutes=10)).isoformat(timespec="minutes"),
    )
    pedido = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_passageiro).get_json()
    sid = pedido["solicitacao"]["id"]
    client.post(f"/api/solicitacoes/{sid}/aceitar", headers=h_motorista)
    minhas = client.get("/api/solicitacoes/minhas", headers=h_passageiro).get_json()["solicitacoes"]
    pin = next(s["pin_embarque"] for s in minhas if s["id"] == sid)
    return {
        "motorista": motorista, "h_motorista": h_motorista,
        "passageiro": passageiro, "h_passageiro": h_passageiro,
        "carona": carona, "sid": sid, "pin": pin,
    }


@pytest.fixture
def concluida(client, viagem):
    """A mesma viagem, ja iniciada, com embarque por PIN e concluida."""
    cid, sid = viagem["carona"]["id"], viagem["sid"]
    assert client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"]).status_code == 200
    assert client.post(f"/api/solicitacoes/{sid}/embarque", json={"pin": viagem["pin"]},
                       headers=viagem["h_motorista"]).status_code == 200
    assert client.post(f"/api/caronas/{cid}/concluir", headers=viagem["h_motorista"]).status_code == 200
    return viagem
