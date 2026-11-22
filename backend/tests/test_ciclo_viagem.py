"""
Ciclo da viagem (inspirado no Uber): iniciar -> embarque com PIN / falta -> concluir,
mais GPS da viagem, teto do rateio e valor sugerido.
"""
from datetime import datetime, timedelta

from caronauvv.caronas.models import PosicaoGps
from caronauvv.ext.db import db


def test_inicia_viagem_e_expira_pedidos_pendentes(client, viagem, novo_aluno):
    _, h_pedro = novo_aluno("100000003", "Pedro")
    cid = viagem["carona"]["id"]
    pendente = client.post(f"/api/caronas/{cid}/solicitacoes", json={}, headers=h_pedro).get_json()["solicitacao"]

    resp = client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    assert resp.status_code == 200
    assert resp.get_json()["carona"]["status"] == "em_andamento"
    assert resp.get_json()["carona"]["iniciada_em"]

    pedidos = client.get(f"/api/caronas/{cid}/solicitacoes", headers=viagem["h_motorista"]).get_json()
    assert {s["id"]: s["status"] for s in pedidos["solicitacoes"]}[pendente["id"]] == "expirada"


def test_nao_inicia_muito_antes_da_saida(client, novo_aluno, nova_carona):
    _, h = novo_aluno("1", "Kaua")
    carona = nova_carona(h)  # sai daqui a 4 h
    resp = client.post(f"/api/caronas/{carona['id']}/iniciar", headers=h)
    assert resp.status_code == 400
    assert "30 minutos" in resp.get_json()["error"]


def test_nao_inicia_sem_passageiro_confirmado(client, novo_aluno, nova_carona):
    _, h = novo_aluno("1", "Kaua")
    carona = nova_carona(h, data_hora_saida=(datetime.now() + timedelta(minutes=5)).isoformat(timespec="minutes"))
    resp = client.post(f"/api/caronas/{carona['id']}/iniciar", headers=h)
    assert resp.status_code == 400
    assert "Nenhum passageiro" in resp.get_json()["error"]


def test_so_o_motorista_inicia(client, viagem):
    resp = client.post(f"/api/caronas/{viagem['carona']['id']}/iniciar", headers=viagem["h_passageiro"])
    assert resp.status_code == 403


def test_embarque_com_pin_correto(client, viagem):
    client.post(f"/api/caronas/{viagem['carona']['id']}/iniciar", headers=viagem["h_motorista"])
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/embarque", json={"pin": viagem["pin"]},
                       headers=viagem["h_motorista"])
    assert resp.status_code == 200
    assert resp.get_json()["solicitacao"]["embarcou_em"]


def test_embarque_com_pin_errado(client, viagem):
    client.post(f"/api/caronas/{viagem['carona']['id']}/iniciar", headers=viagem["h_motorista"])
    errado = "0000" if viagem["pin"] != "0000" else "1111"
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/embarque", json={"pin": errado},
                       headers=viagem["h_motorista"])
    assert resp.status_code == 400
    assert "PIN incorreto" in resp.get_json()["error"]


def test_embarque_exige_viagem_iniciada(client, viagem):
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/embarque", json={"pin": viagem["pin"]},
                       headers=viagem["h_motorista"])
    assert resp.status_code == 400


def test_pin_mal_formatado(client, viagem):
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/embarque", json={"pin": "12a"},
                       headers=viagem["h_motorista"])
    assert resp.status_code == 400
    assert resp.get_json()["campos"]["pin"] == "O PIN tem 4 números."


def test_marcar_falta_conta_na_reputacao(client, viagem):
    cid = viagem["carona"]["id"]
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/falta", headers=viagem["h_motorista"])
    assert resp.get_json()["solicitacao"]["faltou"] is True
    perfil = client.get(f"/api/usuarios/{viagem['passageiro']['id']}", headers=viagem["h_motorista"]).get_json()
    assert perfil["usuario"]["reputacao"]["faltas"] == 1


def test_passageiro_nao_desiste_depois_que_a_viagem_comecou(client, viagem):
    client.post(f"/api/caronas/{viagem['carona']['id']}/iniciar", headers=viagem["h_motorista"])
    resp = client.post(f"/api/solicitacoes/{viagem['sid']}/cancelar", headers=viagem["h_passageiro"])
    assert resp.status_code == 400


def test_conclui_viagem_em_andamento_antes_do_horario(client, viagem):
    cid = viagem["carona"]["id"]
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    resp = client.post(f"/api/caronas/{cid}/concluir", headers=viagem["h_motorista"])
    assert resp.status_code == 200
    assert resp.get_json()["carona"]["status"] == "concluida"


def test_gps_so_com_viagem_em_andamento(client, viagem):
    cid = viagem["carona"]["id"]
    ponto = {"lat": -20.35, "lng": -40.29}
    assert client.post(f"/api/caronas/{cid}/posicao", json=ponto, headers=viagem["h_motorista"]).status_code == 400
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    assert client.post(f"/api/caronas/{cid}/posicao", json=ponto, headers=viagem["h_motorista"]).status_code == 201
    assert client.post(f"/api/caronas/{cid}/posicao", json=ponto, headers=viagem["h_passageiro"]).status_code == 403
    assert db.session.scalar(db.select(db.func.count()).select_from(PosicaoGps)) == 1


def test_gps_valida_coordenadas(client, viagem):
    resp = client.post(f"/api/caronas/{viagem['carona']['id']}/posicao", json={"lat": 200, "lng": 0},
                       headers=viagem["h_motorista"])
    assert resp.status_code == 400
    assert "lat" in resp.get_json()["campos"]


# ==========================================================
# RATEIO: carona solidaria (teto) e valor sugerido
# ==========================================================
def test_rateio_tem_teto(client, novo_aluno, nova_carona):
    _, h = novo_aluno("1", "Kaua")
    resp = client.post("/api/caronas", json={
        "bairro_origem": "Itapua", "endereco_origem": "Rua A", "vagas": 2, "valor_por_passageiro": 20,
        "data_hora_saida": (datetime.now() + timedelta(hours=3)).isoformat(timespec="minutes"),
    }, headers=h)
    assert resp.status_code == 400
    assert "R$ 5,00" in resp.get_json()["error"]


def test_valor_sugerido_divide_o_combustivel(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    resp = client.get("/api/caronas/valor-sugerido?distancia_km=6.2&vagas=3", headers=h).get_json()
    # 0,55/km x 6,2 km / 4 pessoas = R$ 0,85 -> arredonda para R$ 1,00
    assert resp["valor_sugerido"] == 1.0
    assert resp["teto"] == 5.0
    longe = client.get("/api/caronas/valor-sugerido?distancia_km=200&vagas=1", headers=h).get_json()
    assert longe["valor_sugerido"] == 5.0  # nunca passa do teto


def test_observacoes_da_carona(client, novo_aluno, nova_carona):
    _, h = novo_aluno("1", "Kaua")
    carona = nova_carona(h, observacoes="  Cabe mochila  ")
    assert carona["observacoes"] == "Cabe mochila"


def test_busca_nao_mostra_as_proprias_caronas(client, novo_aluno, nova_carona):
    _, h = novo_aluno("1", "Kaua")
    nova_carona(h)
    assert client.get("/api/caronas", headers=h).get_json()["caronas"] == []
