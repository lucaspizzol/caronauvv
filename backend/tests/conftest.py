from datetime import datetime, timedelta

import pytest

from caronauvv import create_app
from caronauvv.config import TestConfig
from caronauvv.ext.db import db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def novo_aluno(client):
    """Cadastra um aluno pela API e devolve (usuario_dict, headers com o token)."""

    def _cadastrar(matricula, nome="Aluno", bairro="Itapua"):
        resp = client.post("/api/auth/cadastro", json={
            "matricula": matricula, "email": f"{matricula}@uvv.br", "nome": nome,
            "telefone": "27999990000", "bairro": bairro, "senha": "123456",
        })
        corpo = resp.get_json()
        return corpo["usuario"], {"Authorization": f"Bearer {corpo['token']}"}

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
