"""
Bairros, CEP, ruas e distancia ate a UVV.

- Bairros: lista curada (dados.py), busca sem acento e sem maiuscula, ranking
  "comeca com" antes de "contem".
- Distancia: Haversine (linha reta) x fator de rota; se o OSRM publico responder,
  usa a distancia real de carro (externos.py, com timeout, cache e plano B).
"""
import math
import unicodedata

from .dados import BAIRROS

UVV = (-20.3617, -40.3075)       # campus Boa Vista, Vila Velha
FATOR_ROTA = 1.35                 # ruas nao sao linha reta: ~35% a mais na Grande Vitoria
CIDADES = ("Vila Velha", "Vitória", "Cariacica", "Serra")


def normalizar(texto: str | None) -> str:
    """'  Itapuã ' -> 'itapua' (sem acento, minusculo, espacos simples)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return " ".join(sem_acento.lower().split())


# Nome repetido em duas cidades (ex.: "Santa Rita"): vale o primeiro da lista (Vila Velha vem antes)
_INDICE = {normalizar(b[0]): b for b in reversed(BAIRROS)}


def _como_dict(nome: str, cidade: str, lat: float, lng: float) -> dict:
    return {"nome": nome, "cidade": cidade, "lat": lat, "lng": lng,
            "distancia_uvv_km": distancia_estimada_km(lat, lng)}


def buscar_bairros(termo: str | None, limite: int = 10) -> list[dict]:
    """Sugestoes enquanto digita. Vazio -> os bairros de Vila Velha mais proximos da UVV."""
    q = normalizar(termo)
    if not q:
        perto = sorted((b for b in BAIRROS if b[1] == "Vila Velha"),
                       key=lambda b: haversine_km(b[2], b[3], *UVV))
        return [_como_dict(*b) for b in perto[:limite]]

    def nota(item) -> int | None:
        chave = normalizar(item[0])
        if chave.startswith(q):
            return 0
        if any(p.startswith(q) for p in chave.split()):
            return 1
        return 2 if q in chave else None

    achados = [(n, b) for b in BAIRROS if (n := nota(b)) is not None]
    # Empate: Vila Velha primeiro (onde fica a UVV), depois ordem alfabetica
    achados.sort(key=lambda x: (x[0], CIDADES.index(x[1][1]), normalizar(x[1][0])))
    return [_como_dict(*b) for _, b in achados[:limite]]


def achar_bairro(nome: str | None) -> dict | None:
    """Bairro exato da lista (ignora acento/maiuscula) ou None."""
    item = _INDICE.get(normalizar(nome))
    return _como_dict(*item) if item else None


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia em linha reta entre dois pontos da Terra (km)."""
    raio = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * raio * math.asin(math.sqrt(a))


def distancia_estimada_km(lat: float, lng: float) -> float:
    """Linha reta ate a UVV x fator de rota, com 1 casa decimal (minimo 1 km)."""
    return max(1.0, round(haversine_km(lat, lng, *UVV) * FATOR_ROTA, 1))


def distancia_ate_uvv(bairro: str) -> dict | None:
    """
    Distancia de carro do centro do bairro ate a UVV.
    Tenta o OSRM (rota real); se cair, usa a estimativa por Haversine.
    """
    from .externos import rota_osrm

    achado = achar_bairro(bairro)
    if achado is None:
        return None
    resposta = {"bairro": achado["nome"], "cidade": achado["cidade"],
                "km": achado["distancia_uvv_km"], "duracao_min": None, "metodo": "estimativa"}
    rota = rota_osrm((achado["lat"], achado["lng"]), UVV)
    if rota:
        resposta.update(km=rota["km"], duracao_min=rota["duracao_min"], metodo="osrm")
    return resposta
