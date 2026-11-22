import unicodedata
from decimal import Decimal


# ==========================================================
# PIX "COPIA E COLA" (BR Code estatico do Banco Central)
# O passageiro paga direto ao motorista; a plataforma so gera o
# codigo (que vira o QR da tela 11) e guarda em pagamentos.pix_copia_cola.
# ==========================================================
def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _ascii(texto: str, limite: int) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento[:limite]


def _crc16(dados: str) -> str:
    # CRC16-CCITT (polinomio 0x1021, valor inicial 0xFFFF), exigido pelo BR Code
    crc = 0xFFFF
    for byte in dados.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def gerar_pix_copia_cola(chave: str, nome: str, cidade: str,
                         valor: Decimal | float | None = None, txid: str = "***") -> str:
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", chave)
    payload = (
        _campo("00", "01")
        + _campo("26", conta)
        + _campo("52", "0000")
        + _campo("53", "986")  # BRL
        + (_campo("54", f"{Decimal(str(valor)):.2f}") if valor is not None else "")
        + _campo("58", "BR")
        + _campo("59", _ascii(nome, 25))
        + _campo("60", _ascii(cidade, 15))
        + _campo("62", _campo("05", txid))
        + "6304"
    )
    return payload + _crc16(payload)
