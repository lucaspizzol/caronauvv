from datetime import datetime, timedelta

from caronauvv.caronas.models import Carona
from caronauvv.ext.db import db


def _mover_saida_para_o_passado(carona_id, horas=1):
    carona = db.session.get(Carona, carona_id)
    carona.data_hora_saida = datetime.now() - timedelta(hours=horas)
    db.session.commit()


# ==========================================================
# CONCLUSAO DA CARONA (funcionalidade 6 do MVP)
# ==========================================================
def test_concluir_depois_da_saida(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1", "Kaua")
    _, h_passageiro = novo_aluno("2", "Ana")
    carona = nova_carona(h_motorista)

    pedido = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_passageiro).get_json()
    client.post(f"/api/solicitacoes/{pedido['solicitacao']['id']}/aceitar", headers=h_motorista)
    _mover_saida_para_o_passado(carona["id"])

    resp = client.post(f"/api/caronas/{carona['id']}/concluir", headers=h_motorista)
    assert resp.status_code == 200
    assert resp.get_json()["carona"]["status"] == "concluida"

    # O historico continua: o passageiro aceito segue na lista de pedidos da carona
    pedidos = client.get(f"/api/caronas/{carona['id']}/solicitacoes", headers=h_motorista).get_json()
    assert [p["status"] for p in pedidos["solicitacoes"]] == ["aceita"]


def test_nao_conclui_antes_do_horario(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1")
    carona = nova_carona(h_motorista)
    resp = client.post(f"/api/caronas/{carona['id']}/concluir", headers=h_motorista)
    assert resp.status_code == 400
    assert "depois do horário" in resp.get_json()["error"]


def test_so_o_motorista_conclui(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1")
    _, h_outro = novo_aluno("2")
    carona = nova_carona(h_motorista)
    _mover_saida_para_o_passado(carona["id"])
    resp = client.post(f"/api/caronas/{carona['id']}/concluir", headers=h_outro)
    assert resp.status_code == 403


def test_pedido_pendente_expira_ao_concluir(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1")
    _, h_passageiro = novo_aluno("2")
    carona = nova_carona(h_motorista)
    client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_passageiro)
    _mover_saida_para_o_passado(carona["id"])

    client.post(f"/api/caronas/{carona['id']}/concluir", headers=h_motorista)
    minhas = client.get("/api/solicitacoes/minhas", headers=h_passageiro).get_json()["solicitacoes"]
    assert minhas[0]["status"] == "expirada"


def test_nao_conclui_carona_cancelada(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1")
    carona = nova_carona(h_motorista)
    client.post(f"/api/caronas/{carona['id']}/cancelar", headers=h_motorista)
    _mover_saida_para_o_passado(carona["id"])
    resp = client.post(f"/api/caronas/{carona['id']}/concluir", headers=h_motorista)
    assert resp.status_code == 400


# ==========================================================
# ERROS SEMPRE EM JSON
# ==========================================================
def test_rota_inexistente_responde_json(client):
    resp = client.get("/api/nao-existe")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Recurso não encontrado."}


def test_metodo_errado_responde_json(client):
    resp = client.delete("/api/health")
    assert resp.status_code == 405
    assert "error" in resp.get_json()


def test_erro_inesperado_vira_500_sem_vazar_detalhes(app, client):
    @app.get("/api/teste-quebra")
    def _quebra():
        raise RuntimeError("detalhe interno")

    resp = client.get("/api/teste-quebra")
    assert resp.status_code == 500
    assert "detalhe interno" not in resp.get_data(as_text=True)


def test_cabecalhos_de_seguranca(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


def test_cors_so_para_origens_liberadas(client):
    liberada = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert liberada.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    estranha = client.get("/api/health", headers={"Origin": "https://site-malicioso.example"})
    assert "Access-Control-Allow-Origin" not in estranha.headers
