from datetime import datetime, timedelta

import pytest

from caronauvv.caronas.models import Carona, Solicitacao
from caronauvv.ext.db import db


@pytest.fixture
def motorista(novo_aluno):
    return novo_aluno("1", "Kaua")


@pytest.fixture
def ana(novo_aluno):
    return novo_aluno("2", "Ana")


@pytest.fixture
def pedro(novo_aluno):
    return novo_aluno("3", "Pedro")


@pytest.fixture
def carona(motorista, nova_carona):
    return nova_carona(motorista[1])


def pedir(client, carona_id, headers, **dados):
    return client.post(f"/api/caronas/{carona_id}/solicitacoes", json=dados, headers=headers)


def acao(client, solicitacao_id, nome, headers):
    return client.post(f"/api/solicitacoes/{solicitacao_id}/{nome}", headers=headers)


def ver_carona(client, carona_id, headers):
    return client.get(f"/api/caronas/{carona_id}", headers=headers).get_json()["carona"]


# ==========================================================
# PEDIR VAGA
# ==========================================================
def test_pedir_vaga(client, carona, ana):
    resp = pedir(client, carona["id"], ana[1], endereco_embarque="Rua Goiania, 45", mensagem="Oi!")
    assert resp.status_code == 201
    s = resp.get_json()["solicitacao"]
    assert s["status"] == "pendente"
    assert s["endereco_embarque"] == "Rua Goiania, 45"
    assert s["pin_embarque"] is None
    # Sem resposta em 30 min, o pedido expira (a carona sai daqui a dias)
    expira = datetime.fromisoformat(s["expira_em"])
    assert timedelta(minutes=28) <= expira - datetime.now() <= timedelta(minutes=31)


def test_prazo_e_o_menor_entre_30_min_e_2h_antes_da_saida(client, motorista, ana, nova_carona):
    # Sai daqui a 2h10: 2 h antes da saida (daqui a 10 min) vence antes dos 30 min
    saida = (datetime.now() + timedelta(hours=2, minutes=10)).replace(second=0, microsecond=0)
    carona = nova_carona(motorista[1], data_hora_saida=saida.isoformat(timespec="minutes"))
    s = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]
    assert datetime.fromisoformat(s["expira_em"]) == saida - timedelta(hours=2)


def test_carona_saindo_em_menos_de_30_min_expira_na_saida(client, motorista, ana, nova_carona):
    carona = nova_carona(motorista[1], data_hora_saida=(datetime.now() + timedelta(minutes=20)).isoformat(timespec="minutes"))
    s = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]
    assert s["expira_em"] == carona["data_hora_saida"]


def test_minutos_para_responder_configuravel(client, motorista, ana, nova_carona, admin):
    resp = client.put("/api/admin/configuracoes", json={"minutos_responder_pedido": "10"}, headers=admin[1])
    assert resp.status_code == 200
    carona = nova_carona(motorista[1])
    s = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]
    expira = datetime.fromisoformat(s["expira_em"])
    assert timedelta(minutes=8) <= expira - datetime.now() <= timedelta(minutes=11)


def test_pedido_expirado_avisa_o_passageiro_pelo_sino(client, carona, motorista, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    db.session.get(Solicitacao, sid).expira_em = datetime.now() - timedelta(minutes=1)
    db.session.commit()

    # O sino (contagem) ja expira o pedido e cria a notificacao
    assert client.get("/api/notificacoes/contagem", headers=ana[1]).get_json()["nao_lidas"] >= 1
    assert db.session.get(Solicitacao, sid).status == "expirada"
    notificacoes = client.get("/api/notificacoes", headers=ana[1]).get_json()["notificacoes"]
    assert notificacoes[0]["tipo"] == "pedido_expirado"
    # Nao avisa duas vezes
    client.get("/api/notificacoes/contagem", headers=motorista[1])
    tipos = [n["tipo"] for n in client.get("/api/notificacoes", headers=ana[1]).get_json()["notificacoes"]]
    assert tipos.count("pedido_expirado") == 1


def test_motorista_nao_pede_vaga_na_propria_carona(client, carona, motorista):
    resp = pedir(client, carona["id"], motorista[1])
    assert resp.status_code == 400
    assert "própria carona" in resp.get_json()["error"]


def test_nao_pede_mesma_carona_duas_vezes(client, carona, ana):
    pedir(client, carona["id"], ana[1])
    assert pedir(client, carona["id"], ana[1]).status_code == 409


def test_nao_pede_vaga_em_carona_cancelada(client, carona, motorista, ana):
    client.post(f"/api/caronas/{carona['id']}/cancelar", headers=motorista[1])
    assert pedir(client, carona["id"], ana[1]).status_code == 400


def test_mensagem_muito_longa(client, carona, ana):
    assert pedir(client, carona["id"], ana[1], mensagem="x" * 301).status_code == 400


def test_reserva_automatica_aceita_na_hora(client, motorista, ana, nova_carona):
    carona = nova_carona(motorista[1], reserva_automatica=True, vagas=1)
    s = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]
    assert s["status"] == "aceita"
    assert len(s["pin_embarque"]) == 4
    assert ver_carona(client, carona["id"], motorista[1])["status"] == "lotada"


# ==========================================================
# ACEITAR / RECUSAR (motorista)
# ==========================================================
def test_aceitar_libera_contato_e_pin(client, carona, motorista, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]

    pedidos = client.get(f"/api/caronas/{carona['id']}/solicitacoes", headers=motorista[1]).get_json()
    assert "telefone" not in pedidos["solicitacoes"][0]["passageiro"]
    assert "telefone" not in ver_carona(client, carona["id"], ana[1])["motorista"]

    resp = acao(client, sid, "aceitar", motorista[1])
    assert resp.status_code == 200
    s = resp.get_json()["solicitacao"]
    assert s["status"] == "aceita"
    assert "pin_embarque" not in s  # o motorista nao ve o PIN, ele digita
    assert s["passageiro"]["telefone"] == "27999990000"

    minhas = client.get("/api/solicitacoes/minhas", headers=ana[1]).get_json()["solicitacoes"]
    assert minhas[0]["pin_embarque"].isdigit()
    assert minhas[0]["carona"]["motorista"]["telefone"] == "27999990000"


def test_so_motorista_aceita_ou_recusa(client, carona, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    assert acao(client, sid, "aceitar", ana[1]).status_code == 403
    assert acao(client, sid, "recusar", ana[1]).status_code == 403


def test_so_motorista_ve_pedidos(client, carona, ana):
    assert client.get(f"/api/caronas/{carona['id']}/solicitacoes", headers=ana[1]).status_code == 403


def test_recusar(client, carona, motorista, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    assert acao(client, sid, "recusar", motorista[1]).get_json()["solicitacao"]["status"] == "recusada"
    assert acao(client, sid, "aceitar", motorista[1]).status_code == 400
    assert pedir(client, carona["id"], ana[1]).status_code == 409  # recusado nao pede de novo


def test_nao_aceita_mais_passageiros_que_vagas(client, motorista, ana, pedro, novo_aluno, nova_carona):
    carona = nova_carona(motorista[1], vagas=1)
    s_ana = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    s_pedro = pedir(client, carona["id"], pedro[1]).get_json()["solicitacao"]["id"]

    acao(client, s_ana, "aceitar", motorista[1])
    assert ver_carona(client, carona["id"], motorista[1])["status"] == "lotada"
    assert acao(client, s_pedro, "aceitar", motorista[1]).status_code == 400

    # Lotada sai da busca e nao recebe novos pedidos
    _, bia = novo_aluno("4", "Bia")
    assert client.get("/api/caronas", headers=bia).get_json()["caronas"] == []
    resp = pedir(client, carona["id"], bia)
    assert resp.status_code == 400
    assert "lotada" in resp.get_json()["error"]


def test_pedido_expirado(client, carona, motorista, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    db.session.get(Solicitacao, sid).expira_em = datetime.now() - timedelta(minutes=1)
    db.session.commit()

    resp = acao(client, sid, "aceitar", motorista[1])
    assert resp.status_code == 400
    assert "expirou" in resp.get_json()["error"]
    minhas = client.get("/api/solicitacoes/minhas", headers=ana[1]).get_json()["solicitacoes"]
    assert minhas[0]["status"] == "expirada"


# ==========================================================
# CANCELAR (passageiro)
# ==========================================================
def test_passageiro_cancela_e_libera_vaga(client, motorista, ana, nova_carona):
    carona = nova_carona(motorista[1], vagas=1)
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    acao(client, sid, "aceitar", motorista[1])

    resp = acao(client, sid, "cancelar", ana[1])
    assert resp.status_code == 200
    assert resp.get_json()["solicitacao"]["status"] == "cancelada"
    carona = ver_carona(client, carona["id"], motorista[1])
    assert (carona["status"], carona["vagas_restantes"]) == ("ativa", 1)

    # Quem cancelou pode pedir de novo (reaproveita o mesmo registro)
    resp = pedir(client, carona["id"], ana[1])
    assert resp.status_code == 201
    assert resp.get_json()["solicitacao"]["id"] == sid
    assert resp.get_json()["solicitacao"]["status"] == "pendente"


def test_so_o_passageiro_cancela_o_pedido(client, carona, motorista, ana, pedro):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    assert acao(client, sid, "cancelar", pedro[1]).status_code == 403
    assert acao(client, sid, "cancelar", motorista[1]).status_code == 403


def test_nao_cancela_depois_que_a_viagem_comecou(client, carona, motorista, ana):
    sid = pedir(client, carona["id"], ana[1]).get_json()["solicitacao"]["id"]
    acao(client, sid, "aceitar", motorista[1])
    db.session.get(Carona, carona["id"]).status = "em_andamento"
    db.session.commit()
    assert acao(client, sid, "cancelar", ana[1]).status_code == 400


def test_solicitacao_inexistente(client, motorista):
    assert acao(client, 999, "aceitar", motorista[1]).status_code == 404


# ==========================================================
# "MINHAS CARONAS" DO PASSAGEIRO
# ==========================================================
def test_minhas_solicitacoes_com_filtro(client, motorista, ana, nova_carona):
    c1 = nova_carona(motorista[1])
    c2 = nova_carona(motorista[1], data_hora_saida=(datetime.now() + timedelta(days=1)).isoformat(timespec="minutes"))
    s1 = pedir(client, c1["id"], ana[1]).get_json()["solicitacao"]["id"]
    pedir(client, c2["id"], ana[1])
    acao(client, s1, "aceitar", motorista[1])

    todas = client.get("/api/solicitacoes/minhas", headers=ana[1]).get_json()["solicitacoes"]
    assert [s["carona"]["id"] for s in todas] == [c2["id"], c1["id"]]  # mais distante primeiro
    aceitas = client.get("/api/solicitacoes/minhas?status=aceita", headers=ana[1]).get_json()["solicitacoes"]
    assert [s["id"] for s in aceitas] == [s1]
