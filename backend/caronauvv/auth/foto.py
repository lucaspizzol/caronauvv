"""
FOTO DE PERFIL

O navegador recorta a foto em quadrado e reduz para 400 x 400 antes de enviar
(frontend/src/utils/imagem.js), entao o arquivo chega com poucos KB. Mesmo assim
o servidor nao confia no que recebe:

- olha os primeiros bytes do arquivo para saber se e mesmo JPEG, PNG ou WebP
  (a extensao e o tipo informado pelo navegador podem ser falsos);
- le a largura e a altura do cabecalho e recusa imagens enormes;
- limita o tamanho em KB.

A foto fica no banco (tabela fotos_perfil) e e servida em /api/fotos/<token>.
O token e aleatorio e muda a cada foto nova: por isso o navegador pode guardar
a imagem em cache por um ano.
"""
import secrets
import struct

from flask import current_app

from caronauvv.errors import ApiError
from caronauvv.ext.db import db

from .models import FotoPerfil, Usuario

FORMATOS = "JPG, PNG ou WebP"


# ==========================================================
# LEITURA DO CABECALHO: (tipo, largura, altura) ou None
# ==========================================================
def _jpeg(dados: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(dados):
        if dados[i] != 0xFF:
            return None
        marcador = dados[i + 1]
        if marcador == 0xFF:           # byte de preenchimento
            i += 1
            continue
        if 0xD0 <= marcador <= 0xD9 or marcador == 0x01:   # marcadores sem tamanho
            i += 2
            continue
        # SOF0..SOF15 (menos DHT, JPG e DAC) guardam altura e largura
        if 0xC0 <= marcador <= 0xCF and marcador not in (0xC4, 0xC8, 0xCC):
            altura, largura = struct.unpack(">HH", dados[i + 5:i + 9])
            return largura, altura
        i += 2 + struct.unpack(">H", dados[i + 2:i + 4])[0]
    return None


def _png(dados: bytes) -> tuple[int, int] | None:
    if len(dados) < 24 or dados[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", dados[16:24])


def _webp(dados: bytes) -> tuple[int, int] | None:
    if len(dados) < 30:
        return None
    bloco = dados[12:16]
    if bloco == b"VP8 " and dados[23:26] == b"\x9d\x01\x2a":      # com perdas
        largura, altura = struct.unpack("<HH", dados[26:30])
        return largura & 0x3FFF, altura & 0x3FFF
    if bloco == b"VP8L" and dados[20] == 0x2F:                     # sem perdas
        bits = struct.unpack("<I", dados[21:25])[0]
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if bloco == b"VP8X":                                           # estendido
        largura = int.from_bytes(dados[24:27], "little") + 1
        altura = int.from_bytes(dados[27:30], "little") + 1
        return largura, altura
    return None


def identificar_imagem(dados: bytes) -> tuple[str, int, int] | None:
    """Descobre o formato pelos primeiros bytes ("numeros magicos") e le o tamanho em pixels."""
    if dados[:3] == b"\xff\xd8\xff":
        mime, medidas = "image/jpeg", _jpeg(dados)
    elif dados[:8] == b"\x89PNG\r\n\x1a\n":
        mime, medidas = "image/png", _png(dados)
    elif dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        mime, medidas = "image/webp", _webp(dados)
    else:
        return None
    if not medidas or medidas[0] < 1 or medidas[1] < 1:
        return None
    return mime, medidas[0], medidas[1]


# ==========================================================
# SALVAR / REMOVER / BUSCAR
# ==========================================================
def salvar_foto(usuario: Usuario, dados: bytes) -> Usuario:
    cfg = current_app.config
    if not dados:
        raise ApiError("Escolha uma foto para enviar.", campos={"foto": "Escolha uma foto."})
    if len(dados) > cfg["FOTO_MAX_KB"] * 1024:
        raise ApiError(f"A foto passou de {cfg['FOTO_MAX_KB']} KB. Envie uma imagem menor.", 413)

    imagem = identificar_imagem(dados)
    if imagem is None:
        raise ApiError(f"Arquivo inválido: envie uma foto em {FORMATOS}.", 415)
    mime, largura, altura = imagem
    if max(largura, altura) > cfg["FOTO_MAX_LADO_PX"]:
        raise ApiError(f"A foto pode ter no máximo {cfg['FOTO_MAX_LADO_PX']} pixels de lado.", 413)

    foto = usuario.foto or FotoPerfil(usuario=usuario)
    foto.token = secrets.token_urlsafe(16)   # endereco novo: o cache da foto antiga nao atrapalha
    foto.mime = mime
    foto.tamanho = len(dados)
    foto.dados = dados
    db.session.add(foto)
    usuario.foto_url = f"/api/fotos/{foto.token}"
    db.session.commit()
    return usuario


def remover_foto(usuario: Usuario) -> Usuario:
    if usuario.foto is not None:
        db.session.delete(usuario.foto)
    usuario.foto_url = None
    db.session.commit()
    return usuario


def buscar_foto(token: str) -> FotoPerfil:
    foto = db.session.scalar(db.select(FotoPerfil).where(FotoPerfil.token == token))
    if foto is None or not foto.usuario.is_active:
        raise ApiError("Foto não encontrada.", 404)
    return foto
