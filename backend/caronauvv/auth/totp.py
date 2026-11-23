"""
TOTP - codigo de 6 numeros que muda a cada 30 segundos (RFC 6238).

E o mesmo padrao do Google Authenticator, Microsoft Authenticator e Authy:
o servidor e o aplicativo guardam o mesmo segredo e, a cada 30 s, os dois
calculam HMAC-SHA1(segredo, numero_do_intervalo). Como so quem tem o segredo
chega no mesmo numero, digitar o codigo prova que a pessoa esta com o celular.

Feito so com a biblioteca padrao do Python (hmac, hashlib, struct, base64),
sem dependencia nova. Os testes conferem com os vetores oficiais da RFC 6238.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

DIGITOS = 6
PERIODO = 30  # segundos que cada codigo vale
JANELA = 1    # aceita 1 intervalo antes/depois (relogio do celular adiantado ou atrasado)


def novo_segredo() -> str:
    """Segredo aleatorio de 160 bits em Base32 (o formato que os aplicativos leem)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _chave(segredo: str) -> bytes:
    limpo = segredo.replace(" ", "").upper()
    return base64.b32decode(limpo + "=" * (-len(limpo) % 8))


def passo_atual(instante: float | None = None) -> int:
    """Numero do intervalo de 30 s desde 01/01/1970 (o "contador" do TOTP)."""
    return int((time.time() if instante is None else instante) // PERIODO)


def codigo_do_passo(segredo: str, passo: int) -> str:
    """HOTP (RFC 4226) do intervalo: HMAC-SHA1 + truncamento dinamico."""
    resumo = hmac.new(_chave(segredo), struct.pack(">Q", passo), hashlib.sha1).digest()
    inicio = resumo[-1] & 0x0F  # os 4 ultimos bits dizem de onde tirar os 4 bytes
    numero = struct.unpack(">I", resumo[inicio:inicio + 4])[0] & 0x7FFFFFFF
    return str(numero % 10**DIGITOS).zfill(DIGITOS)


def codigo_atual(segredo: str, instante: float | None = None) -> str:
    return codigo_do_passo(segredo, passo_atual(instante))


def verificar(segredo: str, codigo: str, instante: float | None = None, depois_do_passo: int | None = None) -> int | None:
    """
    Confere o codigo digitado. Devolve o numero do intervalo que bateu, ou None.

    depois_do_passo: ultimo intervalo ja usado por este usuario. Um codigo so vale
    uma vez, entao quem viu o codigo por cima do ombro nao consegue reaproveitar.
    """
    codigo = "".join(c for c in str(codigo or "") if c.isdigit())
    if len(codigo) != DIGITOS:
        return None
    agora = passo_atual(instante)
    for passo in range(agora - JANELA, agora + JANELA + 1):
        if depois_do_passo is not None and passo <= depois_do_passo:
            continue
        # compare_digest: comparacao em tempo constante (nao vaza quantos digitos estao certos)
        if hmac.compare_digest(codigo_do_passo(segredo, passo), codigo):
            return passo
    return None


def uri_otpauth(segredo: str, conta: str, emissor: str = "CaronaUVV") -> str:
    """Endereco que vira o QR Code lido pelo aplicativo autenticador."""
    rotulo = quote(f"{emissor}:{conta}")
    return (
        f"otpauth://totp/{rotulo}?secret={segredo}&issuer={quote(emissor)}"
        f"&algorithm=SHA1&digits={DIGITOS}&period={PERIODO}"
    )
