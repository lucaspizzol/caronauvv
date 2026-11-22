"""
Avaliacao mutua "as cegas" (BlaBlaCar), reputacao do perfil publico e pagamento do rateio.
"""
from datetime import datetime, timedelta

from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.ext.db import db


def avaliar(client, sid, headers, **dados):
    return client.post(f"/api/solicitacoes/{sid}/avaliacao", json={"nota": 5, **dados}, headers=headers)


# ==========================================================
# AVALIACOES
# ==========================================================
def test_pendentes_aparecem_para_os_dois_lados(client, concluida):
    p = client.get("/api/avaliacoes/pendentes", headers=concluida["h_passageiro"]).get_json()["pendentes"]
    m = client.get("/api/avaliacoes/pendentes", headers=concluida["h_motorista"]).get_json()["pendentes"]
    assert p[0]["papel_avaliado"] == "motorista" and p[0]["avaliado"]["nome"] == "Kaua Araujo"
    assert m[0]["papel_avaliado"] == "passageiro" and m[0]["avaliado"]["nome"] == "Ana Souza"


def test_avaliacao_some_das_pendentes(client, concluida):
    assert avaliar(client, concluida["sid"], concluida["h_passageiro"], tags=["Pontual"]).status_code == 201
    assert client.get("/api/avaliacoes/pendentes", headers=concluida["h_passageiro"]).get_json()["pendentes"] == []


def test_nota_fica_escondida_ate_os_dois_avaliarem(client, concluida):
    motorista_id = concluida["motorista"]["id"]
    avaliar(client, concluida["sid"], concluida["h_passageiro"], nota=4, tags=["Pontual"])
    perfil = client.get(f"/api/usuarios/{motorista_id}", headers=concluida["h_passageiro"]).get_json()["usuario"]
    assert perfil["reputacao"]["total_avaliacoes"] == 0  # ainda "as cegas"

    avaliar(client, concluida["sid"], concluida["h_motorista"], nota=5)
    perfil = client.get(f"/api/usuarios/{motorista_id}", headers=concluida["h_passageiro"]).get_json()["usuario"]
    assert perfil["reputacao"]["nota_media"] == 4.0
    assert perfil["avaliacoes"][0]["tags"] == ["Pontual"]


def test_nota_aparece_sozinha_depois_do_prazo(client, concluida):
    avaliar(client, concluida["sid"], concluida["h_passageiro"], nota=3)
    db.session.execute(db.update(Avaliacao).values(created_at=datetime.now() - timedelta(days=8)))
    db.session.commit()
    perfil = client.get(f"/api/usuarios/{concluida['motorista']['id']}",
                        headers=concluida["h_motorista"]).get_json()["usuario"]
    assert perfil["reputacao"]["nota_media"] == 3.0


def test_nao_avalia_duas_vezes(client, concluida):
    avaliar(client, concluida["sid"], concluida["h_passageiro"])
    assert avaliar(client, concluida["sid"], concluida["h_passageiro"]).status_code == 409


def test_nao_avalia_carona_nao_concluida(client, viagem):
    resp = avaliar(client, viagem["sid"], viagem["h_passageiro"])
    assert resp.status_code == 400
    assert "concluída" in resp.get_json()["error"]


def test_terceiro_nao_avalia(client, concluida, novo_aluno):
    _, h_outro = novo_aluno("100000009", "Intruso")
    assert avaliar(client, concluida["sid"], h_outro).status_code == 403


def test_nota_fora_da_escala(client, concluida):
    resp = avaliar(client, concluida["sid"], concluida["h_passageiro"], nota=6)
    assert resp.status_code == 400
    assert resp.get_json()["campos"]["nota"] == "O valor máximo é 5."


def test_tag_do_lado_errado(client, concluida):
    # "Pagou certinho" e elogio de passageiro, nao de motorista
    resp = avaliar(client, concluida["sid"], concluida["h_passageiro"], tags=["Pagou certinho"])
    assert resp.status_code == 400


def test_tag_inexistente(client, concluida):
    resp = avaliar(client, concluida["sid"], concluida["h_passageiro"], tags=["Voa baixo"])
    assert resp.status_code == 400


# ==========================================================
# REPUTACAO E PERFIL PUBLICO
# ==========================================================
def test_reputacao_conta_viagens_e_selos(client, concluida):
    perfil = client.get(f"/api/usuarios/{concluida['motorista']['id']}",
                        headers=concluida["h_passageiro"]).get_json()["usuario"]
    rep = perfil["reputacao"]
    assert rep["viagens_motorista"] == 1
    assert rep["nivel"] == "Calouro"
    assert {"codigo": "email_uvv", "texto": "E-mail UVV confirmado"} in rep["selos"]
    assert "telefone" not in perfil  # perfil publico nao expoe contato


def test_cartao_da_carona_traz_reputacao_do_motorista(client, novo_aluno, nova_carona):
    _, h_motorista = novo_aluno("1", "Kaua")
    _, h_ana = novo_aluno("2", "Ana")
    nova_carona(h_motorista)
    carona = client.get("/api/caronas", headers=h_ana).get_json()["caronas"][0]
    assert carona["motorista"]["reputacao"]["nivel"] == "Calouro"


def test_perfil_de_usuario_inexistente(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    assert client.get("/api/usuarios/999", headers=h).status_code == 404


# ==========================================================
# PAGAMENTO (Pix copia e cola direto para o motorista)
# ==========================================================
def test_pix_exige_chave_do_motorista(client, viagem):
    resp = client.get(f"/api/solicitacoes/{viagem['sid']}/pix", headers=viagem["h_passageiro"])
    assert resp.status_code == 400
    assert "chave Pix" in resp.get_json()["error"]


def test_gera_pix_e_informa_pagamento(client, viagem):
    client.put("/api/auth/me", json={"chave_pix": "kaua@uvv.br"}, headers=viagem["h_motorista"])
    pix = client.get(f"/api/solicitacoes/{viagem['sid']}/pix", headers=viagem["h_passageiro"]).get_json()["pagamento"]
    assert pix["status"] == "pendente" and pix["valor"] == 1.5
    assert "br.gov.bcb.pix" in pix["pix_copia_cola"] and "54041.50" in pix["pix_copia_cola"]

    pago = client.post(f"/api/solicitacoes/{viagem['sid']}/pagamento", json={"metodo": "pix"},
                       headers=viagem["h_passageiro"])
    assert pago.get_json()["pagamento"]["status"] == "pago"
    avisos = client.get("/api/notificacoes", headers=viagem["h_motorista"]).get_json()["notificacoes"]
    assert any(n["tipo"] == "pagamento_informado" for n in avisos)
    # nao registra duas vezes
    assert client.post(f"/api/solicitacoes/{viagem['sid']}/pagamento", json={},
                       headers=viagem["h_passageiro"]).status_code == 400


def test_pagamento_so_para_participantes(client, viagem, novo_aluno):
    _, h_outro = novo_aluno("100000009", "Intruso")
    assert client.get(f"/api/solicitacoes/{viagem['sid']}/pix", headers=h_outro).status_code == 403


def test_carona_gratuita_nao_tem_pagamento(client, novo_aluno, nova_carona):
    _, h_m = novo_aluno("1", "Kaua")
    _, h_p = novo_aluno("2", "Ana")
    carona = nova_carona(h_m, valor_por_passageiro=0, reserva_automatica=True)
    sid = client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_p).get_json()["solicitacao"]["id"]
    resp = client.get(f"/api/solicitacoes/{sid}/pix", headers=h_p)
    assert resp.status_code == 400 and "gratuita" in resp.get_json()["error"]
