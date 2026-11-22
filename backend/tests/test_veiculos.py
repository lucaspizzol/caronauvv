import pytest

from caronauvv.caronas.models import Carona
from caronauvv.ext.db import db


@pytest.fixture
def kaua(novo_aluno):
    return novo_aluno("1", "Kaua")


def cadastrar_carro(client, headers, placa="KAU2B34"):
    return client.post("/api/veiculos", json={"modelo": "HB20", "cor": "Branco", "placa": placa},
                       headers=headers)


def test_cadastrar_veiculo_normaliza_placa(client, kaua):
    resp = cadastrar_carro(client, kaua[1], placa="kau-2b34")
    assert resp.status_code == 201
    assert resp.get_json()["veiculo"]["placa"] == "KAU2B34"


@pytest.mark.parametrize("placa", ["", "AB1234", "1234ABC", "KAU2B345"])
def test_placa_invalida(client, kaua, placa):
    assert cadastrar_carro(client, kaua[1], placa=placa).status_code == 400


def test_placa_duplicada(client, kaua, novo_aluno):
    cadastrar_carro(client, kaua[1])
    _, ana = novo_aluno("2", "Ana")
    assert cadastrar_carro(client, ana, placa="KAU-2B34").status_code == 409


def test_listar_so_os_meus(client, kaua, novo_aluno):
    cadastrar_carro(client, kaua[1])
    _, ana = novo_aluno("2", "Ana")
    cadastrar_carro(client, ana, placa="ANA1A11")
    veiculos = client.get("/api/veiculos", headers=kaua[1]).get_json()["veiculos"]
    assert [v["placa"] for v in veiculos] == ["KAU2B34"]


def test_editar_veiculo(client, kaua, novo_aluno):
    vid = cadastrar_carro(client, kaua[1]).get_json()["veiculo"]["id"]
    resp = client.put(f"/api/veiculos/{vid}", json={"cor": "Prata"}, headers=kaua[1])
    assert resp.get_json()["veiculo"]["cor"] == "Prata"

    _, ana = novo_aluno("2", "Ana")
    assert client.put(f"/api/veiculos/{vid}", json={"cor": "Azul"}, headers=ana).status_code == 404


def test_remover_veiculo_em_uso(client, kaua, nova_carona):
    vid = cadastrar_carro(client, kaua[1]).get_json()["veiculo"]["id"]
    carona = nova_carona(kaua[1], veiculo_id=vid)
    assert carona["veiculo"]["modelo"] == "HB20"

    assert client.delete(f"/api/veiculos/{vid}", headers=kaua[1]).status_code == 400

    client.post(f"/api/caronas/{carona['id']}/cancelar", headers=kaua[1])
    assert client.delete(f"/api/veiculos/{vid}", headers=kaua[1]).status_code == 200
    assert db.session.get(Carona, carona["id"]).veiculo_id is None
    assert client.get("/api/veiculos", headers=kaua[1]).get_json()["veiculos"] == []
