from datetime import datetime, timedelta

import pytest

from caronauvv.auth.models import Veiculo
from caronauvv.caronas.models import Carona, Solicitacao
from caronauvv.ext.db import db


def daqui(**delta) -> str:
    return (datetime.now() + timedelta(**delta)).isoformat(timespec="minutes")


def dados_carona(**extra) -> dict:
    return {
        "bairro_origem": "Itapua",
        "endereco_origem": "Rua Itaunas, 120",
        "data_hora_saida": daqui(hours=2),
        "vagas": 2,
        "valor_por_passageiro": 1.5,
        **extra,
    }


@pytest.fixture
def motorista(novo_aluno):
    return novo_aluno("1", "Kaua")


@pytest.fixture
def passageiro(novo_aluno):
    return novo_aluno("2", "Ana")


@pytest.fixture
def carona_id(client, motorista):
    _, headers = motorista
    return client.post("/api/caronas", json=dados_carona(), headers=headers).get_json()["carona"]["id"]


def adicionar_solicitacao(carona_id, passageiro_id, status):
    s = Solicitacao(carona_id=carona_id, passageiro_id=passageiro_id, status=status)
    db.session.add(s)
    db.session.commit()
    return s


# ==========================================================
# CRIAR
# ==========================================================
def test_criar_carona(client, motorista):
    usuario, headers = motorista
    resp = client.post("/api/caronas", json=dados_carona(), headers=headers)
    assert resp.status_code == 201
    carona = resp.get_json()["carona"]
    assert carona["status"] == "ativa"
    assert carona["vagas_restantes"] == 2
    assert carona["valor_por_passageiro"] == 1.5
    assert carona["destino"] == "UVV - Entrada principal"
    assert carona["motorista"]["id"] == usuario["id"]


def test_criar_carona_exige_login(client):
    assert client.post("/api/caronas", json=dados_carona()).status_code == 401


def test_nao_cria_carona_no_passado(client, motorista):
    _, headers = motorista
    resp = client.post("/api/caronas", json=dados_carona(data_hora_saida=daqui(minutes=-5)), headers=headers)
    assert resp.status_code == 400
    assert "futuro" in resp.get_json()["error"]


@pytest.mark.parametrize("extra", [
    {"vagas": 0},
    {"vagas": 7},
    {"vagas": "duas"},
    {"valor_por_passageiro": -1},
    {"sentido": "lado"},
    {"data_hora_saida": "amanha"},
    {"bairro_origem": ""},
])
def test_criar_carona_valida_campos(client, motorista, extra):
    _, headers = motorista
    assert client.post("/api/caronas", json=dados_carona(**extra), headers=headers).status_code == 400


def test_criar_carona_com_veiculo_de_outro(client, motorista, passageiro):
    _, headers = motorista
    carro_da_ana = Veiculo(usuario_id=passageiro[0]["id"], modelo="Onix", cor="Prata", placa="ANA1A11")
    db.session.add(carro_da_ana)
    db.session.commit()
    resp = client.post("/api/caronas", json=dados_carona(veiculo_id=carro_da_ana.id), headers=headers)
    assert resp.status_code == 400


# ==========================================================
# LISTAR / BUSCA
# ==========================================================
def test_listar_ordena_por_horario_e_filtra_bairro(client, motorista, passageiro):
    _, headers = motorista
    client.post("/api/caronas", json=dados_carona(data_hora_saida=daqui(hours=5)), headers=headers)
    client.post("/api/caronas", json=dados_carona(data_hora_saida=daqui(hours=3)), headers=headers)
    client.post("/api/caronas", json=dados_carona(bairro_origem="Praia da Costa"), headers=headers)

    caronas = client.get("/api/caronas?bairro=itapua", headers=passageiro[1]).get_json()["caronas"]
    assert len(caronas) == 2
    assert caronas[0]["data_hora_saida"] < caronas[1]["data_hora_saida"]


def test_listar_filtra_data_e_faixa_de_horario(client, motorista, passageiro):
    _, headers = motorista
    amanha = (datetime.now() + timedelta(days=1)).date().isoformat()
    for hora in ("17:30", "18:30", "19:30"):
        client.post("/api/caronas", json=dados_carona(data_hora_saida=f"{amanha}T{hora}"), headers=headers)

    resp = client.get(f"/api/caronas?data={amanha}&hora_inicio=18:00&hora_fim=19:00", headers=passageiro[1])
    caronas = resp.get_json()["caronas"]
    assert [c["data_hora_saida"][-5:] for c in caronas] == ["18:30"]


def test_listar_filtro_invalido(client, passageiro):
    assert client.get("/api/caronas?data=ontem", headers=passageiro[1]).status_code == 400


def test_listar_esconde_canceladas_lotadas_e_passadas(client, motorista, passageiro, carona_id):
    _, headers = motorista
    lotada = client.post("/api/caronas", json=dados_carona(vagas=1), headers=headers).get_json()["carona"]["id"]
    adicionar_solicitacao(lotada, passageiro[0]["id"], "aceita")
    client.put(f"/api/caronas/{lotada}", json={"vagas": 1}, headers=headers)  # recalcula -> lotada

    cancelada = client.post("/api/caronas", json=dados_carona(), headers=headers).get_json()["carona"]["id"]
    client.post(f"/api/caronas/{cancelada}/cancelar", headers=headers)

    passada = db.session.get(Carona, client.post("/api/caronas", json=dados_carona(),
                                                 headers=headers).get_json()["carona"]["id"])
    passada.data_hora_saida = datetime.now() - timedelta(hours=1)
    db.session.commit()

    ids = [c["id"] for c in client.get("/api/caronas", headers=passageiro[1]).get_json()["caronas"]]
    assert ids == [carona_id]


def test_minhas_caronas_inclui_canceladas(client, motorista, passageiro, carona_id):
    _, headers = motorista
    client.post(f"/api/caronas/{carona_id}/cancelar", headers=headers)
    minhas = client.get("/api/caronas/minhas", headers=headers).get_json()["caronas"]
    assert [c["status"] for c in minhas] == ["cancelada"]
    assert client.get("/api/caronas/minhas", headers=passageiro[1]).get_json()["caronas"] == []


# ==========================================================
# DETALHE: telefone e placa so apos aceite
# ==========================================================
def test_contato_so_aparece_apos_aceite(client, motorista, passageiro, novo_aluno):
    usuario, headers = motorista
    carro = Veiculo(usuario_id=usuario["id"], modelo="HB20", cor="Branco", placa="KAU2B34")
    db.session.add(carro)
    db.session.commit()
    carona_id = client.post("/api/caronas", json=dados_carona(veiculo_id=carro.id),
                            headers=headers).get_json()["carona"]["id"]
    adicionar_solicitacao(carona_id, passageiro[0]["id"], "aceita")
    _, outro_headers = novo_aluno("3", "Pedro")

    def ver(h):
        return client.get(f"/api/caronas/{carona_id}", headers=h).get_json()["carona"]

    estranho = ver(outro_headers)
    assert "telefone" not in estranho["motorista"]
    assert "placa" not in estranho["veiculo"]

    for h in (headers, passageiro[1]):
        carona = ver(h)
        assert carona["motorista"]["telefone"] == "27999990000"
        assert carona["veiculo"]["placa"] == "KAU2B34"


def test_detalhe_inexistente(client, passageiro):
    assert client.get("/api/caronas/999", headers=passageiro[1]).status_code == 404


# ==========================================================
# EDITAR
# ==========================================================
def test_editar_carona(client, motorista, carona_id):
    _, headers = motorista
    resp = client.put(f"/api/caronas/{carona_id}", json={"vagas": 4, "valor_por_passageiro": 1},
                      headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["carona"]["vagas"] == 4


def test_so_motorista_edita(client, passageiro, carona_id):
    resp = client.put(f"/api/caronas/{carona_id}", json={"vagas": 4}, headers=passageiro[1])
    assert resp.status_code == 403


def test_editar_para_o_passado(client, motorista, carona_id):
    _, headers = motorista
    resp = client.put(f"/api/caronas/{carona_id}", json={"data_hora_saida": daqui(hours=-1)}, headers=headers)
    assert resp.status_code == 400


def test_vagas_nao_ficam_abaixo_dos_aceitos_e_status_acompanha(client, motorista, passageiro,
                                                                novo_aluno, carona_id):
    _, headers = motorista
    adicionar_solicitacao(carona_id, passageiro[0]["id"], "aceita")
    adicionar_solicitacao(carona_id, novo_aluno("3", "Pedro")[0]["id"], "aceita")

    url = f"/api/caronas/{carona_id}"
    assert client.put(url, json={"vagas": 1}, headers=headers).status_code == 400
    assert client.put(url, json={"vagas": 2}, headers=headers).get_json()["carona"]["status"] == "lotada"
    assert client.put(url, json={"vagas": 3}, headers=headers).get_json()["carona"]["status"] == "ativa"


# ==========================================================
# CANCELAR
# ==========================================================
def test_cancelar_cancela_solicitacoes_em_aberto(client, motorista, passageiro, novo_aluno, carona_id):
    _, headers = motorista
    aceita = adicionar_solicitacao(carona_id, passageiro[0]["id"], "aceita")
    pendente = adicionar_solicitacao(carona_id, novo_aluno("3", "Pedro")[0]["id"], "pendente")
    recusada = adicionar_solicitacao(carona_id, novo_aluno("4", "Bia")[0]["id"], "recusada")

    resp = client.post(f"/api/caronas/{carona_id}/cancelar", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["carona"]["status"] == "cancelada"
    assert (aceita.status, pendente.status, recusada.status) == ("cancelada", "cancelada", "recusada")


def test_so_motorista_cancela(client, passageiro, carona_id):
    assert client.post(f"/api/caronas/{carona_id}/cancelar", headers=passageiro[1]).status_code == 403


def test_nao_cancela_nem_edita_carona_cancelada(client, motorista, carona_id):
    _, headers = motorista
    client.post(f"/api/caronas/{carona_id}/cancelar", headers=headers)
    assert client.post(f"/api/caronas/{carona_id}/cancelar", headers=headers).status_code == 400
    assert client.put(f"/api/caronas/{carona_id}", json={"vagas": 3}, headers=headers).status_code == 400
