"""Entrada e saida do passageiro (com GPS), resumo da viagem, mapa e medias do painel."""
from datetime import datetime, timedelta

from caronauvv.caronas.models import Carona, PosicaoGps, Solicitacao
from caronauvv.ext.db import db


def iniciar(client, v):
    assert client.post(f"/api/caronas/{v['carona']['id']}/iniciar", headers=v["h_motorista"]).status_code == 200


def embarcar(client, v, **gps):
    return client.post(f"/api/solicitacoes/{v['sid']}/embarque", json={"pin": v["pin"], **gps}, headers=v["h_motorista"])


def desembarcar(client, v, headers, **gps):
    return client.post(f"/api/solicitacoes/{v['sid']}/desembarque", json=gps, headers=headers)


def resumo(client, v, headers):
    return client.get(f"/api/caronas/{v['carona']['id']}/resumo", headers=headers)


def test_embarque_com_gps(client, viagem):
    iniciar(client, viagem)
    assert embarcar(client, viagem, lat=-20.35, lng=-40.29).status_code == 200
    s = db.session.get(Solicitacao, viagem["sid"])
    assert (s.metodo_embarque, s.embarque_gps_lat, s.embarque_gps_lng) == ("pin+gps", -20.35, -40.29)


def test_embarque_com_gps_invalido(client, viagem):
    iniciar(client, viagem)
    assert embarcar(client, viagem, lat=200, lng=0).status_code == 400


def test_passageiro_registra_o_desembarque(client, viagem):
    iniciar(client, viagem)
    embarcar(client, viagem)
    resp = desembarcar(client, viagem, viagem["h_passageiro"], lat=-20.36, lng=-40.30)
    assert resp.status_code == 200
    assert resp.get_json()["solicitacao"]["desembarcou_em"] is not None
    # O motorista e avisado
    tipos = [n["tipo"] for n in client.get("/api/notificacoes", headers=viagem["h_motorista"]).get_json()["notificacoes"]]
    assert "desembarque" in tipos
    # Nao registra duas vezes
    assert desembarcar(client, viagem, viagem["h_motorista"]).status_code == 400


def test_motorista_registra_o_desembarque(client, viagem):
    iniciar(client, viagem)
    embarcar(client, viagem)
    assert desembarcar(client, viagem, viagem["h_motorista"]).status_code == 200
    tipos = [n["tipo"] for n in client.get("/api/notificacoes", headers=viagem["h_passageiro"]).get_json()["notificacoes"]]
    assert "desembarque" in tipos


def test_regras_do_desembarque(client, viagem, novo_aluno):
    # viagem nao iniciada
    assert desembarcar(client, viagem, viagem["h_motorista"]).status_code == 400
    iniciar(client, viagem)
    # ainda nao embarcou
    assert desembarcar(client, viagem, viagem["h_motorista"]).status_code == 400
    embarcar(client, viagem)
    # outra pessoa
    _, intruso = novo_aluno("555", "Intruso")
    assert desembarcar(client, viagem, intruso).status_code == 403


def test_concluir_desembarca_quem_estava_a_bordo(client, concluida):
    s = db.session.get(Solicitacao, concluida["sid"])
    assert s.desembarcou_em is not None


def test_resumo_da_viagem(client, viagem):
    iniciar(client, viagem)
    embarcar(client, viagem, lat=-20.3477, lng=-40.2949)
    # Simula a trilha: entrada ha 20 min, 3 pontos ate a UVV, saida agora
    carona = db.session.get(Carona, viagem["carona"]["id"])
    s = db.session.get(Solicitacao, viagem["sid"])
    agora = datetime.now()
    carona.iniciada_em = agora - timedelta(minutes=25)
    s.embarcou_em = agora - timedelta(minutes=20)
    for i, (lat, lng) in enumerate([(-20.3477, -40.2949), (-20.3550, -40.3000), (-20.3617, -40.3075)]):
        db.session.add(PosicaoGps(carona_id=carona.id, lat=lat, lng=lng, registrada_em=agora - timedelta(minutes=19 - i * 9)))
    db.session.commit()
    desembarcar(client, viagem, viagem["h_passageiro"], lat=-20.3617, lng=-40.3075)
    client.post(f"/api/caronas/{carona.id}/concluir", headers=viagem["h_motorista"])

    r = resumo(client, viagem, viagem["h_motorista"]).get_json()["resumo"]
    assert len(r["trilha"]) == 3
    assert r["distancia_pela_trilha"] is True
    assert 1.5 <= r["distancia_km"] <= 3
    assert r["duracao_min"] == 25
    assert r["velocidade_media_kmh"] > 0
    p = r["passageiros"][0]
    assert p["minutos_a_bordo"] == 20
    assert p["entrada"] == {"lat": -20.3477, "lng": -40.2949}
    assert p["saida"] == {"lat": -20.3617, "lng": -40.3075}
    assert p["km_a_bordo"] > 1


def test_resumo_so_para_participantes(client, concluida, novo_aluno, admin):
    _, intruso = novo_aluno("556", "Intruso")
    assert resumo(client, concluida, intruso).status_code == 403
    assert resumo(client, concluida, concluida["h_passageiro"]).status_code == 200
    assert resumo(client, concluida, admin[1]).status_code == 200


def test_passageiro_ve_so_a_propria_linha(client, viagem, novo_aluno):
    # segundo passageiro na mesma carona
    _, bia = novo_aluno("557", "Bia")
    sid2 = client.post(f"/api/caronas/{viagem['carona']['id']}/solicitacoes", json={}, headers=bia).get_json()["solicitacao"]["id"]
    client.post(f"/api/solicitacoes/{sid2}/aceitar", headers=viagem["h_motorista"])
    nomes = [p["nome"] for p in resumo(client, viagem, viagem["h_passageiro"]).get_json()["resumo"]["passageiros"]]
    assert nomes == ["Ana Souza"]
    assert len(resumo(client, viagem, viagem["h_motorista"]).get_json()["resumo"]["passageiros"]) == 2


def test_medias_no_painel(client, concluida, admin):
    carona = db.session.get(Carona, concluida["carona"]["id"])
    carona.iniciada_em = carona.data_hora_saida + timedelta(minutes=4)
    carona.concluida_em = carona.iniciada_em + timedelta(minutes=18)
    carona.distancia_km = 6
    db.session.commit()
    medias = client.get("/api/admin/resumo", headers=admin[1]).get_json()["resumo"]["medias"]
    assert medias["viagens_medidas"] == 1
    assert medias["tempo_medio_viagem_min"] == 18
    assert medias["atraso_medio_saida_min"] == 4
    assert medias["velocidade_media_kmh"] == 20


def test_link_da_familia_tem_a_trilha(client, viagem):
    iniciar(client, viagem)
    client.post(f"/api/caronas/{viagem['carona']['id']}/posicao", json={"lat": -20.35, "lng": -40.29}, headers=viagem["h_motorista"])
    link = client.post(f"/api/caronas/{viagem['carona']['id']}/compartilhar", headers=viagem["h_passageiro"]).get_json()
    token = link.get("link", link).get("token") if isinstance(link.get("link", link), dict) else None
    assert token, link
    publico = client.get(f"/api/acompanhar/{token}").get_json()
    assert publico["viagem"]["trilha"] == [[-20.35, -40.29]]
