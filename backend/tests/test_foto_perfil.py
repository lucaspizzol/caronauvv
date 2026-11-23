"""Foto de perfil: envio, validacao do arquivo, exibicao e moderacao."""
import io
import struct
import zlib

import pytest

from caronauvv.auth.foto import identificar_imagem
from caronauvv.auth.models import FotoPerfil, Usuario
from caronauvv.ext.db import db
from caronauvv.ext.db.seed import PASTA_FOTOS

JPEG = (PASTA_FOTOS / "kaua.jpg").read_bytes()   # 320 x 320


def png(largura=64, altura=64) -> bytes:
    """PNG valido de uma cor so, montado na mao (sem depender de biblioteca de imagem)."""
    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    linhas = b"".join(b"\x00" + b"\x1d\x4e\xa3" * largura for _ in range(altura))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(linhas)) + bloco(b"IEND", b""))


def webp(largura=200, altura=100) -> bytes:
    """So o cabecalho de um WebP estendido (VP8X): basta para ler o formato e as medidas."""
    corpo = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" \
        + (largura - 1).to_bytes(3, "little") + (altura - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(corpo)) + b"WEBP" + corpo


def enviar(client, headers, dados: bytes, nome="foto.jpg"):
    return client.put("/api/auth/me/foto", data={"foto": (io.BytesIO(dados), nome)},
                      headers=headers, content_type="multipart/form-data")


# ==========================================================
# LEITURA DO CABECALHO
# ==========================================================
def test_identifica_formato_e_medidas():
    assert identificar_imagem(JPEG) == ("image/jpeg", 320, 320)
    assert identificar_imagem(png(64, 48)) == ("image/png", 64, 48)
    assert identificar_imagem(webp(200, 100)) == ("image/webp", 200, 100)


@pytest.mark.parametrize("dados", [
    b"", b"GIF89a" + b"\x00" * 40, b"%PDF-1.7 texto", b"<svg xmlns='http://www.w3.org/2000/svg'/>",
    b"\xff\xd8\xff" + b"\x00" * 40,          # comeco de JPEG, mas sem o cabecalho das medidas
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 30,     # assinatura de PNG sem o bloco IHDR
])
def test_arquivo_que_nao_e_imagem(dados):
    assert identificar_imagem(dados) is None


# ==========================================================
# ENVIO
# ==========================================================
def test_envia_foto_e_ela_aparece_no_perfil(client, novo_aluno):
    usuario, headers = novo_aluno(1, "Kaua Araujo")
    assert usuario["foto_url"] is None

    resp = enviar(client, headers, JPEG)
    assert resp.status_code == 200, resp.get_json()
    url = resp.get_json()["usuario"]["foto_url"]
    assert url.startswith("/api/fotos/")

    # a tag <img> nao manda token: a foto abre pelo endereco aleatorio
    foto = client.get(url)
    assert foto.status_code == 200
    assert foto.mimetype == "image/jpeg"
    assert foto.data == JPEG
    assert "immutable" in foto.headers["Cache-Control"]
    assert foto.headers["X-Content-Type-Options"] == "nosniff"

    # outros alunos recebem o endereco no perfil publico e na busca
    _, h_outro = novo_aluno(2, "Ana Souza")
    publico = client.get(f"/api/usuarios/{usuario['id']}", headers=h_outro).get_json()["usuario"]
    assert publico["foto_url"] == url


def test_o_tipo_vem_do_conteudo_e_nao_do_nome_do_arquivo(client, novo_aluno):
    _, headers = novo_aluno(1)
    url = enviar(client, headers, png(), nome="foto.jpg").get_json()["usuario"]["foto_url"]
    assert client.get(url).mimetype == "image/png"


def test_foto_nova_troca_o_endereco_e_apaga_a_antiga(client, novo_aluno):
    _, headers = novo_aluno(1)
    antiga = enviar(client, headers, JPEG).get_json()["usuario"]["foto_url"]
    nova = enviar(client, headers, png()).get_json()["usuario"]["foto_url"]
    assert nova != antiga
    assert client.get(antiga).status_code == 404
    assert client.get(nova).status_code == 200
    assert db.session.scalar(db.select(db.func.count()).select_from(FotoPerfil)) == 1


def test_remove_a_foto(client, novo_aluno):
    _, headers = novo_aluno(1)
    url = enviar(client, headers, JPEG).get_json()["usuario"]["foto_url"]
    resp = client.delete("/api/auth/me/foto", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["foto_url"] is None
    assert client.get(url).status_code == 404
    # remover de novo nao da erro
    assert client.delete("/api/auth/me/foto", headers=headers).status_code == 200


# ==========================================================
# VALIDACAO
# ==========================================================
def test_exige_login(client):
    resp = client.put("/api/auth/me/foto", data={"foto": (io.BytesIO(JPEG), "f.jpg")},
                      content_type="multipart/form-data")
    assert resp.status_code == 401


def test_sem_arquivo(client, novo_aluno):
    _, headers = novo_aluno(1)
    resp = client.put("/api/auth/me/foto", data={}, headers=headers, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "foto" in resp.get_json()["campos"]


@pytest.mark.parametrize("dados", [
    b"MZ\x90\x00 programa disfarcado de foto",
    b"<script>alert(1)</script>",
    b"GIF89a" + b"\x00" * 100,
])
def test_recusa_arquivo_que_nao_e_foto(client, novo_aluno, dados):
    _, headers = novo_aluno(1)
    resp = enviar(client, headers, dados, nome="foto.jpg")
    assert resp.status_code == 415
    assert "JPG, PNG ou WebP" in resp.get_json()["error"]


def test_recusa_foto_pesada(client, app, novo_aluno):
    _, headers = novo_aluno(1)
    app.config["FOTO_MAX_KB"] = 4
    resp = enviar(client, headers, JPEG)   # ~8 KB
    assert resp.status_code == 413
    assert "4 KB" in resp.get_json()["error"]


def test_recusa_foto_com_medidas_enormes(client, novo_aluno):
    """Um PNG pequeno em KB pode ter milhares de pixels e travar o navegador de quem ve."""
    _, headers = novo_aluno(1)
    resp = enviar(client, headers, webp(5000, 5000))
    assert resp.status_code == 413
    assert "1024 pixels" in resp.get_json()["error"]


def test_requisicao_gigante_e_barrada_antes_de_ler(client, app, novo_aluno):
    _, headers = novo_aluno(1)
    app.config["MAX_CONTENT_LENGTH"] = 1024
    resp = enviar(client, headers, JPEG)
    assert resp.status_code == 413
    assert resp.get_json() == {"error": "Arquivo grande demais."}


def test_nao_da_para_apontar_a_foto_para_um_site_de_fora(client, novo_aluno):
    """foto_url so muda pelo envio do arquivo; pelo PUT /me o campo e ignorado."""
    _, headers = novo_aluno(1)
    resp = client.put("/api/auth/me", json={"foto_url": "https://site-de-fora.example/rastreador.png"}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["foto_url"] is None


def test_foto_inexistente(client):
    assert client.get("/api/fotos/nao-existe").status_code == 404


def test_foto_de_conta_suspensa_nao_abre(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    url = enviar(client, headers, JPEG).get_json()["usuario"]["foto_url"]
    db.session.get(Usuario, usuario["id"]).is_active = False
    db.session.commit()
    assert client.get(url).status_code == 404


def test_apagar_o_usuario_apaga_a_foto(client, novo_aluno):
    usuario, headers = novo_aluno(1)
    enviar(client, headers, JPEG)
    db.session.delete(db.session.get(Usuario, usuario["id"]))
    db.session.commit()
    assert db.session.scalar(db.select(db.func.count()).select_from(FotoPerfil)) == 0


# ==========================================================
# MODERACAO (painel admin)
# ==========================================================
def test_admin_remove_foto_inadequada_e_avisa_o_aluno(client, novo_aluno, admin):
    usuario, headers = novo_aluno(1)
    url = enviar(client, headers, JPEG).get_json()["usuario"]["foto_url"]
    _, h_admin = admin

    resp = client.delete(f"/api/admin/usuarios/{usuario['id']}/foto", headers=h_admin)
    assert resp.status_code == 200
    assert resp.get_json()["usuario"]["foto_url"] is None
    assert client.get(url).status_code == 404
    avisos = client.get("/api/notificacoes", headers=headers).get_json()["notificacoes"]
    assert avisos[0]["titulo"] == "Foto de perfil removida"

    # sem foto: erro claro; aluno comum: proibido
    assert client.delete(f"/api/admin/usuarios/{usuario['id']}/foto", headers=h_admin).status_code == 400
    assert client.delete(f"/api/admin/usuarios/{usuario['id']}/foto", headers=headers).status_code == 403
