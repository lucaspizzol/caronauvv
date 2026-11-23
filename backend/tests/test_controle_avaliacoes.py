"""Controle de avaliacoes: alerta de nota baixa, exclusao automatica por media e painel em tempo real."""
from datetime import datetime, timedelta

from caronauvv.admin.models import Configuracao
from caronauvv.auth.models import Usuario
from caronauvv.caronas.models import Carona, PosicaoGps
from caronauvv.ext.db import db
from caronauvv.seguranca.models import Alerta


def avaliar(client, sid, headers, nota, comentario=None):
    corpo = {"nota": nota}
    if comentario:
        corpo["comentario"] = comentario
    return client.post(f"/api/solicitacoes/{sid}/avaliacao", json=corpo, headers=headers)


def alertas(tipo):
    return list(db.session.scalars(db.select(Alerta).where(Alerta.tipo == tipo)))


def regra(chave, valor):
    db.session.add(Configuracao(chave=chave, valor=valor))
    db.session.commit()


# ==========================================================
# ALERTA DE NOTA BAIXA
# ==========================================================
def test_nota_abaixo_de_4_gera_alerta_e_avisa_o_admin(client, concluida, admin):
    resp = avaliar(client, concluida["sid"], concluida["h_motorista"], 3, "Atrasou bastante.")
    assert resp.status_code == 201, resp.get_json()
    [alerta] = alertas("avaliacao_baixa")
    assert alerta.usuario_id == concluida["passageiro"]["id"]
    assert "Nota 3" in alerta.detalhe and "Atrasou bastante." in alerta.detalhe
    avisos = client.get("/api/notificacoes", headers=admin[1]).get_json()["notificacoes"]
    assert any(n["tipo"] == "avaliacao_baixa" for n in avisos)
    # o alerta aparece na aba Alertas do painel
    tipos = [a["tipo"] for a in client.get("/api/admin/alertas", headers=admin[1]).get_json()["alertas"]]
    assert "avaliacao_baixa" in tipos


def test_nota_4_ou_mais_nao_gera_alerta(client, concluida, admin):
    assert avaliar(client, concluida["sid"], concluida["h_motorista"], 4).status_code == 201
    assert avaliar(client, concluida["sid"], concluida["h_passageiro"], 5).status_code == 201
    assert alertas("avaliacao_baixa") == []


def test_limite_do_alerta_vem_do_painel(client, concluida, admin):
    regra("nota_alerta_avaliacao", "5")
    avaliar(client, concluida["sid"], concluida["h_motorista"], 4)
    assert len(alertas("avaliacao_baixa")) == 1


# ==========================================================
# EXCLUSAO AUTOMATICA (media abaixo de 3)
# ==========================================================
def test_media_abaixo_de_3_exclui_o_aluno_automaticamente(client, concluida, admin, nova_carona):
    passageiro_id = concluida["passageiro"]["id"]
    # o passageiro tinha outra carona marcada: deve ser cancelada junto
    outra = nova_carona(concluida["h_motorista"])
    pedido = client.post(f"/api/caronas/{outra['id']}/solicitacoes", json={}, headers=concluida["h_passageiro"]).get_json()
    client.post(f"/api/solicitacoes/{pedido['solicitacao']['id']}/aceitar", headers=concluida["h_motorista"])

    assert avaliar(client, concluida["sid"], concluida["h_motorista"], 2).status_code == 201

    usuario = db.session.get(Usuario, passageiro_id)
    assert usuario.is_active is False
    assert usuario.suspenso_motivo.startswith("Exclusão automática: média 2,0")
    [alerta] = alertas("exclusao_automatica")
    assert alerta.usuario_id == passageiro_id
    # sai do app na hora: o token antigo para de valer e o login e recusado
    assert client.get("/api/auth/me", headers=concluida["h_passageiro"]).status_code in (401, 403)
    login = client.post("/api/auth/login", json={"login": usuario.email, "senha": "123456"})
    assert login.status_code in (401, 403)
    # o pedido na outra carona foi cancelado e a vaga voltou
    vagas = client.get(f"/api/caronas/{outra['id']}", headers=concluida["h_motorista"]).get_json()["carona"]
    assert vagas["vagas_restantes"] == vagas["vagas"]


def test_motorista_tambem_e_excluido(client, concluida, admin):
    assert avaliar(client, concluida["sid"], concluida["h_passageiro"], 1).status_code == 201
    motorista = db.session.get(Usuario, concluida["motorista"]["id"])
    assert motorista.is_active is False
    assert "média 1,0" in motorista.suspenso_motivo


def test_media_3_ou_mais_nao_exclui(client, concluida, admin):
    avaliar(client, concluida["sid"], concluida["h_motorista"], 3)
    assert db.session.get(Usuario, concluida["passageiro"]["id"]).is_active is True
    assert alertas("exclusao_automatica") == []


def test_minimo_de_avaliacoes_antes_de_excluir(client, concluida, admin):
    regra("avaliacoes_minimas_exclusao", "3")
    avaliar(client, concluida["sid"], concluida["h_motorista"], 1)
    # so 1 avaliacao: alerta de nota baixa sim, exclusao nao
    assert db.session.get(Usuario, concluida["passageiro"]["id"]).is_active is True
    assert len(alertas("avaliacao_baixa")) == 1


def test_administrador_nunca_e_excluido(client, concluida, admin):
    motorista = db.session.get(Usuario, concluida["motorista"]["id"])
    motorista.is_admin = True
    db.session.commit()
    avaliar(client, concluida["sid"], concluida["h_passageiro"], 1)
    assert db.session.get(Usuario, motorista.id).is_active is True


def test_admin_pode_reativar_quem_foi_excluido(client, concluida, admin):
    avaliar(client, concluida["sid"], concluida["h_motorista"], 1)
    pid = concluida["passageiro"]["id"]
    resp = client.post(f"/api/admin/usuarios/{pid}/suspender", json={"ativo": True}, headers=admin[1])
    assert resp.status_code == 200
    u = resp.get_json()["usuario"]
    assert u["is_active"] is True and u["suspenso_motivo"] is None
    assert u["media_recebida"] == 1.0 and u["avaliacoes_recebidas"] == 1


def test_suspensao_manual_guarda_o_motivo(client, novo_aluno, admin):
    aluno, _ = novo_aluno(5)
    u = client.post(f"/api/admin/usuarios/{aluno['id']}/suspender", json={"ativo": False}, headers=admin[1]).get_json()["usuario"]
    assert u["is_active"] is False and "administração" in u["suspenso_motivo"]


# ==========================================================
# PAINEL EM TEMPO REAL
# ==========================================================
def test_feed_de_avaliacoes_para_o_admin(client, concluida, admin):
    avaliar(client, concluida["sid"], concluida["h_motorista"], 3, "Demorou no ponto.")
    dados = client.get("/api/admin/avaliacoes", headers=admin[1]).get_json()
    [a] = dados["avaliacoes"]
    assert a["nota"] == 3 and a["papel_avaliado"] == "passageiro"
    assert a["revelada"] is False   # o aluno ainda nao ve (as cegas), mas o admin ve
    assert dados["estatisticas"]["total"] == 1
    assert dados["estatisticas"]["distribuicao"]["3"] == 1
    assert dados["estatisticas"]["alertas_abertos"] == 1
    assert dados["em_risco"][0]["media"] == 3.0
    assert dados["regras"] == {"nota_alerta": 4.0, "media_minima": 3.0, "minimo_avaliacoes": 1.0}
    # filtro: so notas baixas
    assert client.get("/api/admin/avaliacoes?nota_maxima=2", headers=admin[1]).get_json()["avaliacoes"] == []


def test_feed_lista_excluidos_automaticamente(client, concluida, admin):
    avaliar(client, concluida["sid"], concluida["h_motorista"], 1)
    excluidos = client.get("/api/admin/avaliacoes", headers=admin[1]).get_json()["excluidos"]
    assert [e["id"] for e in excluidos] == [concluida["passageiro"]["id"]]


def test_viagens_ao_vivo_com_posicao(client, viagem, admin):
    cid, sid = viagem["carona"]["id"], viagem["sid"]
    client.post(f"/api/caronas/{cid}/iniciar", headers=viagem["h_motorista"])
    client.post(f"/api/solicitacoes/{sid}/embarque", json={"pin": viagem["pin"]}, headers=viagem["h_motorista"])
    agora = datetime.now()
    db.session.add_all([
        PosicaoGps(carona_id=cid, lat=-20.3400, lng=-40.2900, registrada_em=agora - timedelta(minutes=1)),
        PosicaoGps(carona_id=cid, lat=-20.3450, lng=-40.2950, registrada_em=agora),
    ])
    db.session.commit()
    dados = client.get("/api/admin/viagens", headers=admin[1]).get_json()
    [v] = [v for v in dados["viagens"] if v["id"] == cid]
    assert v["status"] == "em_andamento"
    assert v["ultima_posicao"]["lat"] == -20.3450
    assert len(v["trilha"]) == 2
    assert v["velocidade_kmh"] > 0
    assert v["passageiros"][0]["situacao"] == "a_bordo"
    assert dados["totais"]["em_andamento"] == 1 and dados["totais"]["passageiros_a_bordo"] == 1


def test_viagem_antiga_nao_aparece_no_ao_vivo(client, concluida, admin):
    carona = db.session.get(Carona, concluida["carona"]["id"])
    carona.concluida_em = datetime.now() - timedelta(days=1)
    db.session.commit()
    assert client.get("/api/admin/viagens", headers=admin[1]).get_json()["viagens"] == []


def test_aluno_comum_nao_acessa_o_monitor(client, novo_aluno):
    _, h = novo_aluno(9)
    assert client.get("/api/admin/viagens", headers=h).status_code == 403
    assert client.get("/api/admin/avaliacoes", headers=h).status_code == 403
