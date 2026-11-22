"""
Seguranca (contatos de confianca, link da familia, botao de emergencia, denuncias)
e notificacoes geradas pelos eventos da carona.
"""
from caronauvv.seguranca.models import Alerta
from caronauvv.ext.db import db


def tipos(client, headers):
    return [n["tipo"] for n in client.get("/api/notificacoes", headers=headers).get_json()["notificacoes"]]


# ==========================================================
# NOTIFICACOES
# ==========================================================
def test_eventos_geram_notificacoes(client, viagem):
    assert "novo_pedido" in tipos(client, viagem["h_motorista"])
    assert "vaga_confirmada" in tipos(client, viagem["h_passageiro"])


def test_recusa_e_cancelamento_avisam(client, novo_aluno, nova_carona):
    _, h_m = novo_aluno("1", "Kaua")
    _, h_a = novo_aluno("2", "Ana")
    _, h_p = novo_aluno("3", "Pedro")
    carona = nova_carona(h_m)
    s_ana = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_a).get_json()["solicitacao"]
    client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_p)
    client.post(f"/api/solicitacoes/{s_ana['id']}/recusar", headers=h_m)
    client.post(f"/api/caronas/{carona['id']}/cancelar", headers=h_m)
    assert "vaga_recusada" in tipos(client, h_a)
    assert "carona_cancelada" in tipos(client, h_p)
    assert "carona_cancelada" not in tipos(client, h_a)  # Ana ja tinha sido recusada


def test_contagem_e_marcar_lidas(client, viagem):
    h = viagem["h_passageiro"]
    assert client.get("/api/notificacoes/contagem", headers=h).get_json()["nao_lidas"] >= 1
    client.post("/api/notificacoes/lidas", headers=h)
    assert client.get("/api/notificacoes/contagem", headers=h).get_json()["nao_lidas"] == 0


def test_conclusao_convida_para_avaliar(client, concluida):
    assert "avaliacao_pendente" in tipos(client, concluida["h_passageiro"])
    assert "avaliacao_pendente" in tipos(client, concluida["h_motorista"])


# ==========================================================
# CONTATOS DE CONFIANCA
# ==========================================================
def test_contatos_de_confianca(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    resp = client.post("/api/contatos", json={"nome": "Mae", "telefone": "(27) 98888-7777"}, headers=h)
    assert resp.status_code == 201 and resp.get_json()["contato"]["telefone"] == "27988887777"
    cid = resp.get_json()["contato"]["id"]
    assert len(client.get("/api/contatos", headers=h).get_json()["contatos"]) == 1
    assert client.delete(f"/api/contatos/{cid}", headers=h).status_code == 200


def test_limite_de_contatos(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    for i in range(5):
        client.post("/api/contatos", json={"nome": f"C{i}", "telefone": "27988887777"}, headers=h)
    assert client.post("/api/contatos", json={"nome": "X", "telefone": "27988887777"}, headers=h).status_code == 400


def test_nao_apaga_contato_dos_outros(client, novo_aluno):
    _, h_ana = novo_aluno("1", "Ana")
    _, h_pedro = novo_aluno("2", "Pedro")
    cid = client.post("/api/contatos", json={"nome": "Mae", "telefone": "27988887777"},
                      headers=h_ana).get_json()["contato"]["id"]
    assert client.delete(f"/api/contatos/{cid}", headers=h_pedro).status_code == 404


# ==========================================================
# LINK DA FAMILIA (publico, sem login)
# ==========================================================
def test_link_da_familia_mostra_viagem_sem_login(client, viagem):
    cid = viagem["carona"]["id"]
    link = client.post(f"/api/caronas/{cid}/compartilhar", headers=viagem["h_passageiro"]).get_json()["link"]
    publico = client.get(f"/api/acompanhar/{link['token']}")  # sem Authorization
    assert publico.status_code == 200
    v = publico.get_json()["viagem"]
    assert v["compartilhado_por"] == "Ana Souza"
    assert v["motorista"]["nome"] == "Kaua Araujo"
    # mesmo link se pedir de novo
    de_novo = client.post(f"/api/caronas/{cid}/compartilhar", headers=viagem["h_passageiro"]).get_json()["link"]
    assert de_novo["token"] == link["token"]


def test_link_mostra_ultima_posicao_gps(client, viagem):
    cid = viagem["carona"]["id"]
    token = client.post(f"/api/caronas/{cid}/compartilhar", headers=viagem["h_passageiro"]).get_json()["link"]["token"]
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    client.post(f"/api/caronas/{cid}/posicao", json={"lat": -20.35, "lng": -40.29}, headers=viagem["h_motorista"])
    v = client.get(f"/api/acompanhar/{token}").get_json()["viagem"]
    assert v["status"] == "em_andamento"
    assert v["ultima_posicao"]["lat"] == -20.35


def test_link_para_de_funcionar_quando_a_viagem_termina(client, viagem):
    cid = viagem["carona"]["id"]
    token = client.post(f"/api/caronas/{cid}/compartilhar", headers=viagem["h_passageiro"]).get_json()["link"]["token"]
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    client.post(f"/api/caronas/{cid}/concluir", headers=viagem["h_motorista"])
    assert client.get(f"/api/acompanhar/{token}").status_code == 410


def test_so_participante_compartilha(client, viagem, novo_aluno):
    _, h_outro = novo_aluno("100000009", "Intruso")
    resp = client.post(f"/api/caronas/{viagem['carona']['id']}/compartilhar", headers=h_outro)
    assert resp.status_code == 403


def test_link_inexistente(client):
    assert client.get("/api/acompanhar/nao-existe").status_code == 404


# ==========================================================
# BOTAO DE EMERGENCIA
# ==========================================================
def test_sos_cria_alerta_e_avisa_admin(client, viagem, admin):
    resp = client.post(f"/api/caronas/{viagem['carona']['id']}/sos", json={"lat": -20.35, "lng": -40.29},
                       headers=viagem["h_passageiro"])
    corpo = resp.get_json()
    assert resp.status_code == 201
    assert corpo["emergencia"] == "190"
    assert corpo["alerta"]["tipo"] == "botao_panico"
    assert db.session.scalar(db.select(Alerta)).status == "aguardando"
    assert "alerta_seguranca" in tipos(client, admin[1])


def test_sos_so_para_quem_esta_na_viagem(client, viagem, novo_aluno):
    _, h_outro = novo_aluno("100000009", "Intruso")
    assert client.post(f"/api/caronas/{viagem['carona']['id']}/sos", json={}, headers=h_outro).status_code == 403


# ==========================================================
# DENUNCIAS
# ==========================================================
def test_denuncia_de_quem_dividiu_carona(client, viagem, admin):
    resp = client.post("/api/denuncias", json={
        "denunciado_id": viagem["motorista"]["id"], "carona_id": viagem["carona"]["id"],
        "motivo": "direcao_perigosa", "descricao": "Passou no sinal vermelho",
    }, headers=viagem["h_passageiro"])
    assert resp.status_code == 201
    # nao repete enquanto a primeira esta em analise
    resp = client.post("/api/denuncias", json={"denunciado_id": viagem["motorista"]["id"], "motivo": "outro"},
                       headers=viagem["h_passageiro"])
    assert resp.status_code == 409


def test_nao_denuncia_quem_nunca_viajou_junto(client, viagem, novo_aluno):
    estranho, _ = novo_aluno("100000009", "Estranho")
    resp = client.post("/api/denuncias", json={"denunciado_id": estranho["id"], "motivo": "outro"},
                       headers=viagem["h_passageiro"])
    assert resp.status_code == 403


def test_motivo_de_denuncia_invalido(client, viagem):
    resp = client.post("/api/denuncias", json={"denunciado_id": viagem["motorista"]["id"], "motivo": "chato"},
                       headers=viagem["h_passageiro"])
    assert resp.status_code == 400
    assert "motivo" in resp.get_json()["campos"]
