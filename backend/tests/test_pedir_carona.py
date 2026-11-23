"""Pedir carona: fila por bairro/horario, aviso ao publicar carona e prioridade de 15 min."""
from datetime import date, datetime, timedelta

import pytest

from caronauvv.caronas.models import Carona, PedidoCarona, Solicitacao
from caronauvv.ext.db import db

AMANHA = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture
def motorista(novo_aluno):
    return novo_aluno("1", "Kaua")[1]


@pytest.fixture
def ana(novo_aluno):
    return novo_aluno("2", "Ana")[1]


@pytest.fixture
def pedro(novo_aluno):
    return novo_aluno("3", "Pedro")[1]


def entrar(client, headers, **dados):
    corpo = {"bairro": "Itapuã", "sentido": "ida", "data": AMANHA, "hora_inicio": "06:30", "hora_fim": "07:30", **dados}
    return client.post("/api/pedidos-carona", json=corpo, headers=headers)


def carona_amanha(nova_carona, headers, hora="07:00", **extra):
    return nova_carona(headers, data_hora_saida=f"{AMANHA}T{hora}", **extra)


def pedir_vaga(client, carona_id, headers):
    return client.post(f"/api/caronas/{carona_id}/solicitacoes", json={}, headers=headers)


def vencer_prioridade(carona_id):
    db.session.get(Carona, carona_id).prioridade_ate = datetime.now() - timedelta(minutes=1)
    db.session.commit()


# ==========================================================
# ENTRAR NA FILA
# ==========================================================
def test_entrar_na_fila(client, ana):
    resp = entrar(client, ana)
    assert resp.status_code == 201
    pedido = resp.get_json()["pedido"]
    assert (pedido["status"], pedido["posicao"], pedido["bairro"]) == ("aberto", 1, "Itapuã")
    assert client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]["id"] == pedido["id"]


def test_posicao_na_fila_por_ordem_de_chegada(client, ana, pedro):
    entrar(client, ana)
    # "itapua" sem acento cai na mesma fila; faixa que se cruza conta
    pedido = entrar(client, pedro, bairro="ITAPUA", hora_inicio="07:00", hora_fim="08:00").get_json()["pedido"]
    assert pedido["posicao"] == 2
    # faixa que nao se cruza: outra fila
    outro = entrar(client, pedro, hora_inicio="18:00", hora_fim="19:00").get_json()["pedido"]
    assert outro["posicao"] == 1


def test_validacoes_da_fila(client, ana):
    assert entrar(client, ana, hora_fim="06:00").status_code == 400                      # fim antes do inicio
    assert entrar(client, ana, bairro="Rua Itapemirim").status_code == 400               # endereco no bairro
    assert entrar(client, ana, data=date.today().isoformat(), hora_inicio="00:00", hora_fim="00:01").status_code == 400
    assert entrar(client, ana, data=(date.today() + timedelta(days=40)).isoformat()).status_code == 400
    assert entrar(client, ana, hora_inicio="06:00", hora_fim="11:00").status_code == 400  # mais de 4 h
    assert entrar(client, ana, sentido="outro").status_code == 400


def test_maximo_de_3_pedidos_abertos_e_sem_repetir(client, ana):
    assert entrar(client, ana).status_code == 201
    assert entrar(client, ana, hora_inicio="07:00", hora_fim="08:00").status_code == 409  # mesma fila
    assert entrar(client, ana, sentido="volta", hora_inicio="18:00", hora_fim="19:00").status_code == 201
    assert entrar(client, ana, bairro="Glória").status_code == 201
    resp = entrar(client, ana, bairro="Ibes")
    assert resp.status_code == 400
    assert "3 pedidos" in resp.get_json()["error"]


def test_cancelar_e_nao_mexer_no_pedido_dos_outros(client, ana, pedro):
    pid = entrar(client, ana).get_json()["pedido"]["id"]
    assert client.post(f"/api/pedidos-carona/{pid}/cancelar", headers=pedro).status_code == 404
    resp = client.post(f"/api/pedidos-carona/{pid}/cancelar", headers=ana)
    assert resp.get_json()["pedido"]["status"] == "cancelado"
    assert client.post(f"/api/pedidos-carona/{pid}/cancelar", headers=ana).status_code == 400


def test_pedido_expira_quando_a_faixa_passa(client, ana):
    pid = entrar(client, ana).get_json()["pedido"]["id"]
    pedido = db.session.get(PedidoCarona, pid)
    pedido.data = date.today() - timedelta(days=1)
    db.session.commit()
    assert client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]["status"] == "expirado"


def test_fila_exige_login(client):
    assert client.post("/api/pedidos-carona", json={}).status_code == 401


# ==========================================================
# MOTORISTA VE A DEMANDA E A FILA E AVISADA
# ==========================================================
def test_motorista_ve_quantos_alunos_esperam(client, motorista, ana, pedro):
    entrar(client, ana)
    entrar(client, pedro, hora_inicio="06:45", hora_fim="07:15")
    url = f"/api/pedidos-carona/demanda?bairro=itapua&sentido=ida&data_hora={AMANHA}T07:00"
    assert client.get(url, headers=motorista).get_json()["alunos"] == 2
    url = f"/api/pedidos-carona/demanda?bairro=itapua&sentido=ida&data_hora={AMANHA}T07:20"
    assert client.get(url, headers=motorista).get_json()["alunos"] == 1
    assert client.get("/api/pedidos-carona/demanda?bairro=x&data_hora=ontem", headers=motorista).status_code == 400
    assert client.get("/api/pedidos-carona/demanda?sentido=x&data_hora=2030-01-01T07:00", headers=motorista).status_code == 400
    assert client.get(f"/api/pedidos-carona/demanda?bairro=&data_hora={AMANHA}T07:00", headers=motorista).get_json()["alunos"] == 0


def test_carona_nova_avisa_a_fila_e_liga_a_prioridade(client, motorista, ana, nova_carona):
    entrar(client, ana)
    carona = carona_amanha(nova_carona, motorista)
    assert carona["prioridade_ate"] is not None
    notificacoes = client.get("/api/notificacoes", headers=ana).get_json()["notificacoes"]
    assert notificacoes[0]["tipo"] == "carona_da_fila"
    assert "1º da fila" in notificacoes[0]["texto"]
    pedido = client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]
    assert pedido["caronas_compativeis"] == 1


def test_carona_sem_fila_nao_tem_prioridade(client, motorista, ana, nova_carona):
    entrar(client, ana, sentido="volta")   # sentido diferente
    carona = carona_amanha(nova_carona, motorista)
    assert carona["prioridade_ate"] is None


# ==========================================================
# PRIORIDADE
# ==========================================================
def test_so_quem_estava_na_fila_pede_vaga_na_janela(client, motorista, ana, pedro, nova_carona):
    entrar(client, ana)
    carona = carona_amanha(nova_carona, motorista)
    resp = pedir_vaga(client, carona["id"], pedro)   # Pedro nao estava na fila
    assert resp.status_code == 403
    assert "reservada para quem estava na fila" in resp.get_json()["error"]
    assert pedir_vaga(client, carona["id"], ana).status_code == 201
    # Passou a janela: abre para todos
    vencer_prioridade(carona["id"])
    assert pedir_vaga(client, carona["id"], pedro).status_code == 201


def test_entrar_na_fila_depois_da_carona_nao_da_prioridade(client, motorista, ana, nova_carona):
    entrar(client, ana, sentido="volta", hora_inicio="18:00", hora_fim="19:00")
    carona = carona_amanha(nova_carona, motorista)
    assert carona["prioridade_ate"] is None
    entrar(client, ana)   # entrou depois de publicada
    assert pedir_vaga(client, carona["id"], ana).status_code == 201  # sem janela, pede normalmente


def test_reserva_automatica_guarda_a_vaga_do_primeiro(client, motorista, ana, pedro, nova_carona):
    entrar(client, ana)
    entrar(client, pedro)
    carona = carona_amanha(nova_carona, motorista, vagas=1, reserva_automatica=True)
    # Pedro e o 2o: a unica vaga esta guardada para a Ana
    resp = pedir_vaga(client, carona["id"], pedro)
    assert resp.status_code == 403
    assert "guardadas" in resp.get_json()["error"]
    # Ana confirma: vaga dela e o pedido da fila vira atendido
    s = pedir_vaga(client, carona["id"], ana).get_json()["solicitacao"]
    assert s["status"] == "aceita"
    pedido = client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]
    assert (pedido["status"], pedido["carona_id"]) == ("atendido", carona["id"])


def test_falta_recente_perde_a_prioridade(client, motorista, ana, nova_carona):
    entrar(client, ana)
    # Ana faltou numa viagem recente
    antiga = carona_amanha(nova_carona, motorista, hora="09:00")
    vencer_prioridade(antiga["id"])
    db.session.add(Solicitacao(carona_id=antiga["id"], passageiro_id=client.get(
        "/api/auth/me", headers=ana).get_json()["usuario"]["id"], status="aceita", faltou=True))
    db.session.commit()

    carona = carona_amanha(nova_carona, motorista)
    texto = client.get("/api/notificacoes", headers=ana).get_json()["notificacoes"][0]["texto"]
    assert "falta recente" in texto
    assert pedir_vaga(client, carona["id"], ana).status_code == 403
    assert client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]["sem_prioridade_por_falta"]


def test_aceite_manual_atende_o_pedido_da_fila(client, motorista, ana, nova_carona):
    entrar(client, ana)
    carona = carona_amanha(nova_carona, motorista)
    sid = pedir_vaga(client, carona["id"], ana).get_json()["solicitacao"]["id"]
    client.post(f"/api/solicitacoes/{sid}/aceitar", headers=motorista)
    assert client.get("/api/pedidos-carona/minhas", headers=ana).get_json()["pedidos"][0]["status"] == "atendido"


def test_limite_de_pedidos_por_minuto(client, ana):
    for _ in range(10):
        entrar(client, ana, data="2000-01-01")  # invalidos, mas contam no limite
    assert entrar(client, ana).status_code == 429
