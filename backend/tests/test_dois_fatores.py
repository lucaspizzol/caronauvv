"""Verificacao em duas etapas (aplicativo autenticador, TOTP) e codigos de reserva."""
from datetime import datetime, timedelta

import pytest

from caronauvv.auth import totp
from caronauvv.auth.models import CodigoReserva, Usuario
from caronauvv.ext.db import db

# Vetores oficiais da RFC 6238 (segredo "12345678901234567890", SHA-1).
# A RFC mostra 8 digitos; com 6, vale o final do numero.
SEGREDO_RFC = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
VETORES = [(59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
           (1234567890, "005924"), (2000000000, "279037"), (20000000000, "353130")]


# ==========================================================
# ALGORITMO (auth/totp.py)
# ==========================================================
@pytest.mark.parametrize("instante, esperado", VETORES)
def test_totp_bate_com_a_rfc_6238(instante, esperado):
    assert totp.codigo_atual(SEGREDO_RFC, instante) == esperado


def test_totp_aceita_relogio_30s_adiantado_ou_atrasado():
    agora = 1_700_000_000
    for desvio in (-30, 0, 30):
        assert totp.verificar(SEGREDO_RFC, totp.codigo_atual(SEGREDO_RFC, agora + desvio), agora) is not None
    assert totp.verificar(SEGREDO_RFC, totp.codigo_atual(SEGREDO_RFC, agora + 90), agora) is None
    assert totp.verificar(SEGREDO_RFC, totp.codigo_atual(SEGREDO_RFC, agora - 90), agora) is None


def test_totp_codigo_so_vale_uma_vez():
    agora = 1_700_000_000
    codigo = totp.codigo_atual(SEGREDO_RFC, agora)
    passo = totp.verificar(SEGREDO_RFC, codigo, agora)
    assert passo == totp.passo_atual(agora)
    assert totp.verificar(SEGREDO_RFC, codigo, agora, depois_do_passo=passo) is None


@pytest.mark.parametrize("codigo", ["", "12345", "1234567", "abcdef", None])
def test_totp_formato_invalido(codigo):
    assert totp.verificar(SEGREDO_RFC, codigo) is None


def test_totp_aceita_codigo_com_espaco():
    agora = 1_700_000_000
    codigo = totp.codigo_atual(SEGREDO_RFC, agora)
    assert totp.verificar(SEGREDO_RFC, f"{codigo[:3]} {codigo[3:]}", agora) is not None


def test_segredo_e_endereco_do_qr_code():
    segredo = totp.novo_segredo()
    assert len(segredo) == 32 and segredo != totp.novo_segredo()
    uri = totp.uri_otpauth(segredo, "kaua@uvv.br")
    assert uri.startswith("otpauth://totp/CaronaUVV%3Akaua%40uvv.br?secret=" + segredo)
    assert "issuer=CaronaUVV" in uri and "digits=6" in uri and "period=30" in uri


# ==========================================================
# AJUDAS
# ==========================================================
def ativar(client, headers) -> tuple[str, list[str]]:
    """Liga o autenticador pela API. Devolve (segredo, codigos de reserva)."""
    inicio = client.post("/api/auth/2fa/iniciar", headers=headers).get_json()
    resp = client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": totp.codigo_atual(inicio["segredo"])}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    return inicio["segredo"], resp.get_json()["codigos_reserva"]


def liberar_codigo(usuario_id: int) -> None:
    """Nos testes tudo acontece no mesmo intervalo de 30 s; isto libera o codigo atual de novo."""
    db.session.get(Usuario, usuario_id).totp_ultimo_passo = None
    db.session.commit()


def entrar(client, usuario) -> dict:
    resp = client.post("/api/auth/login", json={"login": usuario["email"], "senha": "123456"})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


# ==========================================================
# LIGAR
# ==========================================================
def test_liga_o_autenticador(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    assert usuario["dois_fatores"] is False

    inicio = client.post("/api/auth/2fa/iniciar", headers=headers).get_json()
    assert inicio["uri"].startswith("otpauth://totp/")
    # enquanto o codigo nao for confirmado, a conta continua entrando so com a senha
    assert "token" in entrar(client, usuario)

    resp = client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": totp.codigo_atual(inicio["segredo"])}, headers=headers)
    corpo = resp.get_json()
    assert resp.status_code == 200, corpo
    assert corpo["usuario"]["dois_fatores"] is True
    assert corpo["dois_fatores"]["codigos_restantes"] == 8
    assert len(set(corpo["codigos_reserva"])) == 8
    assert all(len(c) == 9 and c[4] == "-" for c in corpo["codigos_reserva"])

    # o aluno e avisado
    avisos = client.get("/api/notificacoes", headers=headers).get_json()["notificacoes"]
    assert avisos[0]["titulo"] == "Verificação em duas etapas ativada"


def test_codigo_errado_nao_liga(client, novo_aluno):
    _, headers = novo_aluno(1)
    client.post("/api/auth/2fa/iniciar", headers=headers)
    resp = client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": "000000"}, headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()["campos"] == {"codigo": "Código incorreto."}
    assert client.get("/api/auth/2fa", headers=headers).get_json()["dois_fatores"]["ativo"] is False


def test_ligar_exige_a_senha(client, novo_aluno):
    """Quem pegou o celular desbloqueado do aluno nao consegue ligar o autenticador e tranca-lo para fora."""
    _, headers = novo_aluno(1)
    segredo = client.post("/api/auth/2fa/iniciar", headers=headers).get_json()["segredo"]
    resp = client.post("/api/auth/2fa/ativar", json={"senha": "errada", "codigo": totp.codigo_atual(segredo)}, headers=headers)
    assert resp.status_code == 403
    assert resp.get_json()["campos"] == {"senha": "Senha incorreta."}
    assert client.post("/api/auth/2fa/ativar", json={"codigo": totp.codigo_atual(segredo)}, headers=headers).status_code == 400
    assert client.get("/api/auth/2fa", headers=headers).get_json()["dois_fatores"]["ativo"] is False


def test_nao_ativa_sem_iniciar_nem_duas_vezes(client, novo_aluno):
    _, headers = novo_aluno(1)
    assert client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": "123456"}, headers=headers).status_code == 400
    ativar(client, headers)
    assert client.post("/api/auth/2fa/iniciar", headers=headers).status_code == 400
    assert client.post("/api/auth/2fa/ativar", json={"senha": "123456", "codigo": "123456"}, headers=headers).status_code == 400


def test_segredo_e_codigos_nunca_voltam_depois(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, codigos = ativar(client, headers)
    for rota in ("/api/auth/me", "/api/auth/2fa", f"/api/usuarios/{usuario['id']}"):
        texto = client.get(rota, headers=headers).get_data(as_text=True)
        assert segredo not in texto
        assert codigos[0] not in texto
    # no banco os codigos de reserva ficam so como HMAC
    hashes = [c.codigo_hash for c in db.session.scalars(db.select(CodigoReserva))]
    assert len(hashes) == 8 and all(len(h) == 64 for h in hashes)
    assert not any(c.replace("-", "") in h for c in codigos for h in hashes)


# ==========================================================
# LOGIN EM DUAS ETAPAS
# ==========================================================
def test_login_pede_o_codigo_e_so_depois_entrega_o_token(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, _ = ativar(client, headers)
    liberar_codigo(usuario["id"])

    etapa1 = entrar(client, usuario)
    assert etapa1["precisa_2fa"] is True
    assert "token" not in etapa1 and "usuario" not in etapa1

    resp = client.post("/api/auth/login/2fa", json={"desafio": etapa1["desafio"], "codigo": totp.codigo_atual(segredo)})
    corpo = resp.get_json()
    assert resp.status_code == 200, corpo
    assert corpo["usuario"]["id"] == usuario["id"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {corpo['token']}"})
    assert me.status_code == 200


def test_senha_errada_nem_chega_na_segunda_etapa(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    ativar(client, headers)
    resp = client.post("/api/auth/login", json={"login": usuario["email"], "senha": "errada"})
    assert resp.status_code == 401
    assert "desafio" not in resp.get_json()


def test_o_desafio_nao_serve_de_token(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    ativar(client, headers)
    desafio = entrar(client, usuario)["desafio"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {desafio}"}).status_code == 401


def test_codigo_errado_no_login(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    ativar(client, headers)
    desafio = entrar(client, usuario)["desafio"]
    resp = client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": "000000"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Código incorreto."


def test_mesmo_codigo_nao_entra_duas_vezes(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, _ = ativar(client, headers)
    liberar_codigo(usuario["id"])
    codigo = totp.codigo_atual(segredo)
    ok = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, usuario)["desafio"], "codigo": codigo})
    assert ok.status_code == 200
    de_novo = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, usuario)["desafio"], "codigo": codigo})
    assert de_novo.status_code == 401


def test_desafio_invalido_ou_vencido(client, app, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, _ = ativar(client, headers)
    liberar_codigo(usuario["id"])
    resp = client.post("/api/auth/login/2fa", json={"desafio": "inventado", "codigo": totp.codigo_atual(segredo)})
    assert resp.status_code == 401

    desafio = entrar(client, usuario)["desafio"]
    app.config["DOIS_FATORES_DESAFIO_SEG"] = -1   # ja nasce vencido
    resp = client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": totp.codigo_atual(segredo)})
    assert resp.status_code == 401
    assert "tempo" in resp.get_json()["error"]


def test_cinco_codigos_errados_bloqueiam_por_10_minutos(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, _ = ativar(client, headers)
    liberar_codigo(usuario["id"])
    desafio = entrar(client, usuario)["desafio"]
    for _ in range(5):
        assert client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": "000000"}).status_code == 401

    # bloqueado: nem o codigo certo passa
    resp = client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": totp.codigo_atual(segredo)})
    assert resp.status_code == 429
    assert "10 min" in resp.get_json()["error"]

    # passado o tempo, volta a aceitar
    db.session.get(Usuario, usuario["id"]).totp_bloqueado_ate = datetime.now() - timedelta(seconds=1)
    db.session.commit()
    resp = client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": totp.codigo_atual(segredo)})
    assert resp.status_code == 200


# ==========================================================
# CODIGOS DE RESERVA
# ==========================================================
def test_codigo_de_reserva_entra_uma_vez_so(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    _, codigos = ativar(client, headers)

    resp = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, usuario)["desafio"], "codigo": codigos[0]})
    corpo = resp.get_json()
    assert resp.status_code == 200, corpo
    assert corpo["aviso"] == "Você entrou com um código de reserva. Restam 7."

    de_novo = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, usuario)["desafio"], "codigo": codigos[0]})
    assert de_novo.status_code == 401

    # aceita minusculas e sem o traco
    solto = codigos[1].replace("-", "").lower()
    resp = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, usuario)["desafio"], "codigo": solto})
    assert resp.status_code == 200
    assert client.get("/api/auth/2fa", headers=headers).get_json()["dois_fatores"]["codigos_restantes"] == 6


def test_codigo_de_reserva_de_outro_aluno_nao_serve(client, novo_aluno):
    ana, h_ana = novo_aluno(1, "Ana")
    bia, h_bia = novo_aluno(2, "Bia")
    _, codigos_ana = ativar(client, h_ana)
    ativar(client, h_bia)
    resp = client.post("/api/auth/login/2fa", json={"desafio": entrar(client, bia)["desafio"], "codigo": codigos_ana[0]})
    assert resp.status_code == 401


def test_gera_novos_codigos_e_os_antigos_param_de_valer(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, antigos = ativar(client, headers)
    liberar_codigo(usuario["id"])

    resp = client.post("/api/auth/2fa/codigos-reserva", json={"senha": "123456", "codigo": totp.codigo_atual(segredo)}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    novos = resp.get_json()["codigos_reserva"]
    assert len(novos) == 8 and not set(novos) & set(antigos)

    desafio = entrar(client, usuario)["desafio"]
    assert client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": antigos[0]}).status_code == 401
    assert client.post("/api/auth/login/2fa", json={"desafio": desafio, "codigo": novos[0]}).status_code == 200


# ==========================================================
# DESLIGAR
# ==========================================================
def test_desliga_com_senha_e_codigo(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    segredo, _ = ativar(client, headers)
    liberar_codigo(usuario["id"])

    sem_senha = client.post("/api/auth/2fa/desativar", json={"senha": "errada", "codigo": totp.codigo_atual(segredo)}, headers=headers)
    assert sem_senha.status_code == 403
    assert sem_senha.get_json()["campos"] == {"senha": "Senha incorreta."}
    sem_codigo = client.post("/api/auth/2fa/desativar", json={"senha": "123456", "codigo": "000000"}, headers=headers)
    assert sem_codigo.status_code == 400   # 400 e nao 401: o aluno continua logado

    resp = client.post("/api/auth/2fa/desativar", json={"senha": "123456", "codigo": totp.codigo_atual(segredo)}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["usuario"]["dois_fatores"] is False
    assert "token" in entrar(client, usuario)   # voltou a entrar so com a senha
    conta = db.session.get(Usuario, usuario["id"])
    assert conta.totp_segredo is None and conta.codigos_reserva == []


def test_desligar_o_que_nao_esta_ligado(client, novo_aluno):
    _, headers = novo_aluno(1)
    resp = client.post("/api/auth/2fa/desativar", json={"senha": "123456", "codigo": "123456"}, headers=headers)
    assert resp.status_code == 400


def test_rotas_exigem_login(client):
    for rota in ("/api/auth/2fa/iniciar", "/api/auth/2fa/ativar", "/api/auth/2fa/desativar", "/api/auth/2fa/codigos-reserva"):
        assert client.post(rota, json={}).status_code == 401
    assert client.get("/api/auth/2fa").status_code == 401


# ==========================================================
# ADMIN: aluno perdeu o celular e os codigos
# ==========================================================
def test_admin_desliga_o_autenticador_de_quem_perdeu_o_celular(client, novo_aluno, admin):
    usuario, headers = novo_aluno(1)
    ativar(client, headers)
    _, h_admin = admin

    assert client.post(f"/api/admin/usuarios/{usuario['id']}/resetar-2fa", headers=headers).status_code == 403
    resp = client.post(f"/api/admin/usuarios/{usuario['id']}/resetar-2fa", headers=h_admin)
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["usuario"]["dois_fatores"] is False
    assert "token" in entrar(client, usuario)
    # de novo: nao ha o que desligar
    assert client.post(f"/api/admin/usuarios/{usuario['id']}/resetar-2fa", headers=h_admin).status_code == 400


def test_conta_de_exemplo_com_autenticador(app, client):
    """beatriz@uvv.br ja vem com a protecao ligada (chave e codigos de reserva no seed)."""
    from caronauvv.ext.db.seed import CODIGOS_RESERVA_EXEMPLO, SEGREDO_2FA_EXEMPLO, popular_banco

    popular_banco()
    etapa1 = client.post("/api/auth/login", json={"login": "beatriz@uvv.br", "senha": "123456"}).get_json()
    assert etapa1["precisa_2fa"] is True
    pelo_app = client.post("/api/auth/login/2fa", json={"desafio": etapa1["desafio"], "codigo": totp.codigo_atual(SEGREDO_2FA_EXEMPLO)})
    assert pelo_app.status_code == 200
    pela_reserva = client.post("/api/auth/login/2fa", json={"desafio": etapa1["desafio"], "codigo": CODIGOS_RESERVA_EXEMPLO[0]})
    assert pela_reserva.status_code == 200
    # as outras contas de exemplo continuam entrando so com a senha
    assert "token" in client.post("/api/auth/login", json={"login": "kaua@uvv.br", "senha": "123456"}).get_json()
