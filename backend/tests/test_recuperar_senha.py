"""Esqueci minha senha (codigo por e-mail) e encerramento das sessoes antigas."""
from datetime import datetime, timedelta

from caronauvv.auth.models import Usuario
from caronauvv.ext.db import db

MENSAGEM = "Se a conta existir, enviamos um código de 6 números para o e-mail cadastrado."


def pedir(client, login) -> dict:
    resp = client.post("/api/auth/esqueci-senha", json={"login": login})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def entra(client, login, senha) -> bool:
    return client.post("/api/auth/login", json={"login": login, "senha": senha}).status_code == 200


def test_troca_a_senha_com_o_codigo_do_email(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    corpo = pedir(client, usuario["email"])
    assert corpo["message"] == MENSAGEM

    resp = client.post("/api/auth/redefinir-senha",
                       json={"login": usuario["email"], "codigo": corpo["codigo_dev"], "nova_senha": "nova-senha-1"})
    assert resp.status_code == 200, resp.get_json()
    assert not entra(client, usuario["email"], "123456")
    assert entra(client, usuario["email"], "nova-senha-1")


def test_funciona_pela_matricula(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    codigo = pedir(client, usuario["matricula"])["codigo_dev"]
    resp = client.post("/api/auth/redefinir-senha",
                       json={"login": usuario["matricula"], "codigo": codigo, "nova_senha": "outra-senha"})
    assert resp.status_code == 200
    assert entra(client, usuario["matricula"], "outra-senha")


def test_resposta_nao_revela_se_a_conta_existe(client):
    corpo = pedir(client, "ninguem@uvv.br")
    assert corpo == {"message": MENSAGEM}   # mesma mensagem, sem codigo


def test_codigo_fica_guardado_como_hash(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    codigo = pedir(client, usuario["email"])["codigo_dev"]
    conta = db.session.get(Usuario, usuario["id"])
    assert codigo not in conta.reset_codigo_hash and len(conta.reset_codigo_hash) == 64


def test_em_producao_o_codigo_nao_volta_na_resposta(client, app, novo_aluno):
    usuario, _ = novo_aluno(1)
    app.config["MOSTRAR_CODIGO_DEV"] = False
    assert pedir(client, usuario["email"]) == {"message": MENSAGEM}
    assert db.session.get(Usuario, usuario["id"]).reset_codigo_hash is not None


def test_codigo_errado_e_limite_de_tentativas(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    certo = pedir(client, usuario["email"])["codigo_dev"]
    errado = "000000" if certo != "000000" else "111111"
    for _ in range(5):
        resp = client.post("/api/auth/redefinir-senha",
                           json={"login": usuario["email"], "codigo": errado, "nova_senha": "nova-senha-1"})
        assert resp.status_code == 400
        assert resp.get_json()["campos"] == {"codigo": "Código incorreto ou vencido."}
    # depois de 5 erros, nem o codigo certo vale: precisa pedir outro
    resp = client.post("/api/auth/redefinir-senha",
                       json={"login": usuario["email"], "codigo": certo, "nova_senha": "nova-senha-1"})
    assert resp.status_code == 429
    assert entra(client, usuario["email"], "123456")


def test_codigo_vence_e_so_vale_uma_vez(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    codigo = pedir(client, usuario["email"])["codigo_dev"]
    conta = db.session.get(Usuario, usuario["id"])
    conta.reset_expira_em = datetime.now() - timedelta(minutes=1)
    db.session.commit()
    dados = {"login": usuario["email"], "codigo": codigo, "nova_senha": "nova-senha-1"}
    assert client.post("/api/auth/redefinir-senha", json=dados).status_code == 400

    conta.reset_expira_em = datetime.now() + timedelta(minutes=10)
    db.session.commit()
    assert client.post("/api/auth/redefinir-senha", json=dados).status_code == 200
    assert client.post("/api/auth/redefinir-senha", json={**dados, "nova_senha": "terceira-senha"}).status_code == 400


def test_nao_reenvia_codigo_em_menos_de_um_minuto(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    primeiro = pedir(client, usuario["email"])
    assert "codigo_dev" in primeiro
    assert pedir(client, usuario["email"]) == {"message": MENSAGEM}   # nada novo foi enviado

    conta = db.session.get(Usuario, usuario["id"])
    conta.reset_enviado_em = datetime.now() - timedelta(seconds=61)
    db.session.commit()
    segundo = pedir(client, usuario["email"])
    assert "codigo_dev" in segundo
    # o codigo antigo deixa de valer quando um novo e gerado
    if primeiro["codigo_dev"] != segundo["codigo_dev"]:
        resp = client.post("/api/auth/redefinir-senha",
                           json={"login": usuario["email"], "codigo": primeiro["codigo_dev"], "nova_senha": "nova-senha-1"})
        assert resp.status_code == 400


def test_validacao_dos_campos(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    codigo = pedir(client, usuario["email"])["codigo_dev"]
    curta = client.post("/api/auth/redefinir-senha", json={"login": usuario["email"], "codigo": codigo, "nova_senha": "123"})
    assert curta.status_code == 400 and "nova_senha" in curta.get_json()["campos"]
    sem_codigo = client.post("/api/auth/redefinir-senha", json={"login": usuario["email"], "codigo": "12", "nova_senha": "nova-senha-1"})
    assert sem_codigo.status_code == 400 and sem_codigo.get_json()["campos"]["codigo"] == "O código tem 6 números."
    assert client.post("/api/auth/esqueci-senha", json={}).status_code == 400


def test_conta_suspensa_nao_recupera(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    db.session.get(Usuario, usuario["id"]).is_active = False
    db.session.commit()
    assert pedir(client, usuario["email"]) == {"message": MENSAGEM}


def test_avisa_o_aluno_que_a_senha_mudou(client, novo_aluno):
    usuario, _ = novo_aluno(1)
    codigo = pedir(client, usuario["email"])["codigo_dev"]
    client.post("/api/auth/redefinir-senha", json={"login": usuario["email"], "codigo": codigo, "nova_senha": "nova-senha-1"})
    token = client.post("/api/auth/login", json={"login": usuario["email"], "senha": "nova-senha-1"}).get_json()["token"]
    avisos = client.get("/api/notificacoes", headers={"Authorization": f"Bearer {token}"}).get_json()["notificacoes"]
    assert avisos[0]["titulo"] == "Senha alterada"


# ==========================================================
# TROCAR A SENHA DERRUBA OS LOGINS ANTIGOS
# ==========================================================
def test_redefinir_a_senha_encerra_as_sessoes_abertas(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    codigo = pedir(client, usuario["email"])["codigo_dev"]
    client.post("/api/auth/redefinir-senha", json={"login": usuario["email"], "codigo": codigo, "nova_senha": "nova-senha-1"})

    resp = client.get("/api/auth/me", headers=headers)   # token de antes da troca
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Sua senha foi alterada. Faça login novamente."


def test_trocar_a_senha_no_perfil_devolve_token_novo(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    resp = client.put("/api/auth/me", json={"senha_atual": "123456", "nova_senha": "nova-senha-1"}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    novo = {"Authorization": f"Bearer {resp.get_json()['token']}"}
    assert client.get("/api/auth/me", headers=novo).status_code == 200      # este aparelho continua logado
    assert client.get("/api/auth/me", headers=headers).status_code == 401   # os outros saem

    # editar outros dados nao mexe na sessao
    resp = client.put("/api/auth/me", json={"bio": "Oi"}, headers=novo)
    assert "token" not in resp.get_json()
    assert client.get("/api/auth/me", headers=novo).status_code == 200


def test_com_autenticador_a_senha_nova_nao_dispensa_o_codigo(client, novo_aluno):
    from caronauvv.auth import totp

    usuario, headers = novo_aluno(1)
    segredo = client.post("/api/auth/2fa/iniciar", headers=headers).get_json()["segredo"]
    client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": totp.codigo_atual(segredo)}, headers=headers)

    codigo = pedir(client, usuario["email"])["codigo_dev"]
    client.post("/api/auth/redefinir-senha", json={"login": usuario["email"], "codigo": codigo, "nova_senha": "nova-senha-1"})
    etapa1 = client.post("/api/auth/login", json={"login": usuario["email"], "senha": "nova-senha-1"}).get_json()
    assert etapa1["precisa_2fa"] is True and "token" not in etapa1
