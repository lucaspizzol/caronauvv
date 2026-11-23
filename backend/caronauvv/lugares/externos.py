"""
APIS EXTERNAS GRATUITAS (sem chave), sempre chamadas pelo servidor:

- ViaCEP (viacep.com.br): CEP -> rua/bairro/cidade, e busca de rua por nome na cidade.
- OSRM publico (router.project-osrm.org): distancia/tempo de carro entre dois pontos.

Regras de seguranca e boa vizinhanca:
- URLs FIXAS (sem SSRF): o usuario so manda o CEP (8 digitos) ou um trecho de nome,
  que vai codificado na URL; nunca uma URL.
- Timeout curto, cache em memoria e plano B: se a API cair, devolve None e o sistema
  segue com a lista local / estimativa. Nenhum dado pessoal sai do servidor
  (so CEP, nome de rua ou a coordenada do CENTRO do bairro).
- O Nominatim (OpenStreetMap) NAO e usado para sugestao enquanto digita: a politica
  de uso dele proibe autocompletar. Por isso a sugestao de rua vem do ViaCEP.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from threading import Lock

from flask import current_app

USER_AGENT = "CaronaUVV/1.0 (projeto academico; caronas entre alunos)"
TIMEOUT_SEG = 4
CACHE_SEG = 24 * 3600
CIDADES_GRANDE_VITORIA = ("Vila Velha", "Vitória", "Cariacica", "Serra")

_cache: dict[str, tuple[float, object]] = {}
_trava = Lock()


def _do_cache(chave: str):
    with _trava:
        item = _cache.get(chave)
    if item and item[0] > time.time():
        return item[1]
    return None


def _guardar(chave: str, valor) -> None:
    with _trava:
        if len(_cache) > 2000:   # nao deixa a memoria crescer sem limite
            _cache.clear()
        _cache[chave] = (time.time() + CACHE_SEG, valor)


def _get_json(url: str):
    """GET com timeout; qualquer falha (rede, HTTP, JSON) vira None."""
    if current_app.config.get("APIS_EXTERNAS_DESLIGADAS"):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEG) as resp:  # noqa: S310 - URL fixa https
            return json.loads(resp.read(300_000).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - plano B: o sistema segue sem a API
        current_app.logger.warning("API externa indisponivel (%s): %s", url.split("?")[0], exc)
        return None


def _endereco_viacep(item: dict) -> dict:
    return {
        "cep": item.get("cep", ""), "rua": item.get("logradouro", ""),
        "bairro": item.get("bairro", ""), "cidade": item.get("localidade", ""), "uf": item.get("uf", ""),
    }


def consultar_cep(cep: str) -> dict | None:
    """Endereco do CEP, ou None se nao existir / API fora do ar."""
    digitos = re.sub(r"\D", "", cep or "")
    if len(digitos) != 8:
        return None
    chave = f"cep:{digitos}"
    guardado = _do_cache(chave)
    if guardado is not None:
        return guardado or None
    dados = _get_json(f"https://viacep.com.br/ws/{digitos}/json/")
    if not isinstance(dados, dict):
        return None                      # API fora: nao guarda, tenta de novo depois
    resultado = {} if dados.get("erro") else _endereco_viacep(dados)
    _guardar(chave, resultado)
    return resultado or None


def buscar_ruas(texto: str, cidade: str = "Vila Velha") -> list[dict] | None:
    """Ruas cujo nome contem `texto` na cidade (o ViaCEP exige 3+ letras). None = API fora."""
    texto = " ".join((texto or "").split())[:60]
    if cidade not in CIDADES_GRANDE_VITORIA or len(texto) < 3:
        return []
    chave = f"ruas:{cidade}:{texto.lower()}"
    guardado = _do_cache(chave)
    if guardado is not None:
        return guardado
    # safe="": a barra tambem e codificada, entao o texto nunca vira outro caminho na URL
    url = (f"https://viacep.com.br/ws/ES/{urllib.parse.quote(cidade, safe='')}/"
           f"{urllib.parse.quote(texto, safe='')}/json/")
    dados = _get_json(url)
    if not isinstance(dados, list):
        return None
    vistos, ruas = set(), []
    for item in dados:
        if not isinstance(item, dict):
            continue
        endereco = _endereco_viacep(item)
        chave_rua = (endereco["rua"], endereco["bairro"])
        if endereco["rua"] and chave_rua not in vistos:
            vistos.add(chave_rua)
            ruas.append(endereco)
    ruas = ruas[:15]
    _guardar(chave, ruas)
    return ruas


def rota_osrm(origem: tuple[float, float], destino: tuple[float, float]) -> dict | None:
    """Distancia (km) e tempo (min) de carro pelo OSRM publico. None se indisponivel."""
    (lat1, lng1), (lat2, lng2) = origem, destino
    coordenadas = f"{lng1:.5f},{lat1:.5f};{lng2:.5f},{lat2:.5f}"
    chave = f"osrm:{coordenadas}"
    guardado = _do_cache(chave)
    if guardado is not None:
        return guardado
    dados = _get_json(f"https://router.project-osrm.org/route/v1/driving/{coordenadas}?overview=false")
    try:
        rota = dados["routes"][0]
        resultado = {"km": round(rota["distance"] / 1000, 1), "duracao_min": round(rota["duration"] / 60)}
    except (TypeError, KeyError, IndexError):
        return None
    _guardar(chave, resultado)
    return resultado


def limpar_cache() -> None:
    with _trava:
        _cache.clear()
