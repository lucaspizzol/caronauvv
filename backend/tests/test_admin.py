"""Painel da administracao: acesso, indicadores, moderacao, configuracoes e banco."""
from datetime import date

from caronauvv.admin.models import Busca
from caronauvv.ext.db import db
from caronauvv.ext.db.seed import popular_banco


def test_aluno_comum_nao_acessa_o_painel(client, novo_aluno):
    _, h = novo_aluno("1", "Kaua")
    assert client.get("/api/admin/resumo", headers=h).status_code == 403
    assert client.get("/api/admin/resumo").status_code == 401


def admin_do_seed(client):
    """Popula o banco de exemplo e entra com admin@uvv.br."""
    popular_banco()
    token = client.post("/api/auth/login", json={"login": "admin@uvv.br", "senha": "123456"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_resumo_com_dados_de_exemplo(client):
    r = client.get("/api/admin/resumo", headers=admin_do_seed(client)).get_json()["resumo"]
    assert r["viagens"]["concluidas"] == 4
    assert r["viagens"]["km_compartilhados"] > 0
    assert r["confianca"]["denuncias_abertas"] == 1
    assert r["usuarios"]["verificacoes_pendentes"] == 1          # Marina
    assert r["demanda_sem_oferta"][0]["bairro"] == "Glória"       # bairro mais buscado sem carona


def test_busca_por_bairro_fica_registrada(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    client.get("/api/caronas?bairro=Gloria&sentido=ida", headers=h)
    busca = db.session.scalar(db.select(Busca))
    # grava com o nome oficial do bairro (com acento), mesmo digitado sem acento
    assert (busca.bairro, busca.qtd_resultados) == ("Glória", 0)


def test_busca_pela_metade_nao_conta_como_demanda(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    for texto in ("S", "Santa", "rua x"):
        client.get(f"/api/caronas?bairro={texto}&sentido=ida", headers=h)
    assert db.session.scalar(db.select(db.func.count()).select_from(Busca)) == 0


def test_atualizacao_automatica_nao_repete_a_busca(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    for _ in range(5):   # a tela de busca se atualiza sozinha a cada 5 s
        client.get("/api/caronas?bairro=Itapuã&sentido=ida", headers=h)
    assert db.session.scalar(db.select(db.func.count()).select_from(Busca)) == 1


def test_painel_ignora_buscas_antigas_pela_metade(client, admin):
    hoje = date.today()
    db.session.add_all([Busca(bairro=b, sentido="ida", data_desejada=hoje, qtd_resultados=0)
                        for b in ("S", "Gloria", "Glória")])
    db.session.commit()
    demanda = client.get("/api/admin/resumo", headers=admin[1]).get_json()["resumo"]["demanda_sem_oferta"]
    assert demanda == [{"bairro": "Glória", "buscas": 2}]


def test_aprovar_selo_de_verificado(client, admin, novo_aluno):
    aluno, h = novo_aluno("1", "Kaua")
    client.post("/api/auth/solicitar-verificacao", headers=h)
    pendentes = client.get("/api/admin/usuarios?pendentes=1", headers=admin[1]).get_json()["usuarios"]
    assert [u["id"] for u in pendentes] == [aluno["id"]]
    resp = client.post(f"/api/admin/usuarios/{aluno['id']}/verificar", json={"aprovado": True}, headers=admin[1])
    assert resp.get_json()["usuario"]["verificado"] is True
    assert client.get("/api/auth/me", headers=h).get_json()["usuario"]["verificado"] is True


def test_suspender_bloqueia_login_e_cancela_caronas(client, admin, novo_aluno, nova_carona):
    motorista, h_m = novo_aluno("1", "Kaua")
    _, h_a = novo_aluno("2", "Ana")
    carona = nova_carona(h_m)
    client.post(f"/api/caronas/{carona['id']}/solicitacoes", json={}, headers=h_a)

    resp = client.post(f"/api/admin/usuarios/{motorista['id']}/suspender", json={"ativo": False}, headers=admin[1])
    assert resp.get_json()["usuario"]["is_active"] is False
    assert client.get("/api/auth/me", headers=h_m).status_code == 401  # token deixa de valer
    login = client.post("/api/auth/login", json={"login": motorista["email"], "senha": "123456"})
    assert login.status_code == 403
    pedidos = client.get("/api/solicitacoes/minhas", headers=h_a).get_json()["solicitacoes"]
    assert pedidos[0]["status"] == "cancelada"


def test_admin_nao_se_suspende(client, admin):
    resp = client.post(f"/api/admin/usuarios/{admin[0]['id']}/suspender", json={"ativo": False}, headers=admin[1])
    assert resp.status_code == 400


def test_encerrar_denuncia_exige_resolucao(client, admin, viagem):
    client.post("/api/denuncias", json={"denunciado_id": viagem["motorista"]["id"], "motivo": "outro"},
                headers=viagem["h_passageiro"])
    did = client.get("/api/admin/denuncias", headers=admin[1]).get_json()["denuncias"][0]["id"]
    assert client.post(f"/api/admin/denuncias/{did}", json={"status": "encerrada"},
                       headers=admin[1]).status_code == 400
    resp = client.post(f"/api/admin/denuncias/{did}",
                       json={"status": "encerrada", "resolucao": "Motorista advertido", "suspender": True},
                       headers=admin[1])
    d = resp.get_json()["denuncia"]
    assert d["status"] == "encerrada" and d["denunciado"]["is_active"] is False


def test_resolver_alerta(client, admin, viagem):
    client.post(f"/api/caronas/{viagem['carona']['id']}/sos", json={}, headers=viagem["h_passageiro"])
    alerta = client.get("/api/admin/alertas", headers=admin[1]).get_json()["alertas"][0]
    resp = client.post(f"/api/admin/alertas/{alerta['id']}/resolver", headers=admin[1])
    assert resp.get_json()["alerta"]["status"] == "resolvido"


def test_configuracoes_mudam_as_regras(client, admin, novo_aluno):
    popular_banco()
    resp = client.put("/api/admin/configuracoes", json={"valor_maximo_passageiro": "8,00"}, headers=admin[1])
    assert any(c["chave"] == "valor_maximo_passageiro" and c["valor"] == "8.00"
               for c in resp.get_json()["configuracoes"])
    _, h = novo_aluno("1", "Kaua")
    sugerido = client.get("/api/caronas/valor-sugerido?distancia_km=500&vagas=1", headers=h).get_json()
    assert sugerido["teto"] == 8.0


def test_configuracao_invalida(client, admin):
    assert client.put("/api/admin/configuracoes", json={"nao_existe": 1}, headers=admin[1]).status_code == 400
    assert client.put("/api/admin/configuracoes", json={"raio_busca_km": "abc"},
                      headers=admin[1]).status_code == 400


def test_estrutura_do_banco_ao_vivo(client):
    banco = client.get("/api/admin/banco", headers=admin_do_seed(client)).get_json()
    nomes = {t["nome"]: t for t in banco["tabelas"]}
    assert len(nomes) == 19
    assert nomes["usuarios"]["linhas"] >= 8
    solicitacoes = {c["nome"]: c for c in nomes["solicitacoes"]["colunas"]}
    assert solicitacoes["carona_id"]["fk"] == "caronas.id"
    assert solicitacoes["id"]["pk"] is True
