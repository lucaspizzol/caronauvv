"""Bairros (sugestao enquanto digita), CEP, ruas e distancia ate a UVV."""
import io
import json

import pytest

from caronauvv.lugares import externos
from caronauvv.lugares.dados import BAIRROS
from caronauvv.lugares.services import achar_bairro, distancia_estimada_km, haversine_km, normalizar


@pytest.fixture
def aluno(novo_aluno):
    return novo_aluno("1", "Kaua")[1]


# ==========================================================
# LISTA E BUSCA DE BAIRROS
# ==========================================================
def test_lista_tem_os_bairros_de_vila_velha_e_da_grande_vitoria():
    cidades = {cidade for _, cidade, _, _ in BAIRROS}
    assert cidades == {"Vila Velha", "Vitória", "Cariacica", "Serra"}
    assert sum(1 for b in BAIRROS if b[1] == "Vila Velha") > 100
    for nome in ("Itapuã", "Praia da Costa", "Glória", "Boa Vista", "Jardim Camburi", "Coqueiral de Itaparica"):
        assert achar_bairro(nome) is not None, nome
    # sem duplicados na mesma cidade (ignorando acento/maiuscula)
    chaves = [(normalizar(n), c) for n, c, *_ in BAIRROS]
    assert len(chaves) == len(set(chaves))
    # nome repetido em duas cidades: vale o de Vila Velha
    assert achar_bairro("Santa Rita")["cidade"] == "Vila Velha"


def test_busca_sem_acento_e_sem_maiuscula(client):
    nomes = [b["nome"] for b in client.get("/api/lugares/bairros?q=ITAPUA").get_json()["bairros"]]
    assert nomes[0] == "Itapuã"


def test_busca_comeca_com_vem_antes_de_contem(client):
    nomes = [b["nome"] for b in client.get("/api/lugares/bairros?q=praia&limite=20").get_json()["bairros"]]
    assert nomes[0].startswith("Praia")
    assert "Praia da Costa" in nomes
    # "Jardim Praia da Costa" contem "praia" no meio: vem depois das que comecam com "Praia"
    if "Jardim Praia da Costa" in nomes:
        assert nomes.index("Jardim Praia da Costa") > nomes.index("Praia da Costa")


def test_busca_vazia_traz_bairros_perto_da_uvv(client):
    bairros = client.get("/api/lugares/bairros").get_json()["bairros"]
    assert len(bairros) == 10
    assert all(b["cidade"] == "Vila Velha" for b in bairros)
    assert bairros[0]["distancia_uvv_km"] <= 2


def test_busca_sem_resultado_e_limite(client):
    assert client.get("/api/lugares/bairros?q=xyzxyz").get_json()["bairros"] == []
    assert len(client.get("/api/lugares/bairros?q=a&limite=999").get_json()["bairros"]) == 20


def test_distancia_estimada_por_coordenada():
    # Itapua fica a ~1,7 km em linha reta da UVV; com o fator de rota, uns 2-4 km
    itapua = achar_bairro("itapua")
    assert 1.5 <= haversine_km(itapua["lat"], itapua["lng"], -20.3617, -40.3075) <= 2.5
    assert 2 <= itapua["distancia_uvv_km"] <= 4
    assert achar_bairro("Jardim Camburi")["distancia_uvv_km"] > 15
    assert distancia_estimada_km(-20.3617, -40.3075) == 1.0  # na porta da UVV: minimo 1 km


# ==========================================================
# DISTANCIA (OSRM com plano B)
# ==========================================================
def test_distancia_sem_osrm_usa_estimativa(client, aluno):
    resp = client.get("/api/lugares/distancia?bairro=praia da costa", headers=aluno).get_json()
    assert resp["bairro"] == "Praia da Costa"
    assert resp["metodo"] == "estimativa"
    assert resp["km"] > 0


def test_distancia_com_osrm(client, aluno, monkeypatch):
    monkeypatch.setattr(externos, "_get_json", lambda url: {"routes": [{"distance": 7480, "duration": 1130}]})
    resp = client.get("/api/lugares/distancia?bairro=Praia da Costa", headers=aluno).get_json()
    assert (resp["metodo"], resp["km"], resp["duracao_min"]) == ("osrm", 7.5, 19)


def test_distancia_de_bairro_fora_da_lista(client, aluno):
    assert client.get("/api/lugares/distancia?bairro=Inventado", headers=aluno).status_code == 404


def test_rotas_externas_exigem_login(client):
    assert client.get("/api/lugares/cep/29102920").status_code == 401
    assert client.get("/api/lugares/ruas?q=itape").status_code == 401
    assert client.get("/api/lugares/distancia?bairro=Itapua").status_code == 401


# ==========================================================
# CEP E RUAS (ViaCEP), com a API simulada
# ==========================================================
def test_cep(client, aluno, monkeypatch):
    chamadas = []

    def falso(url):
        chamadas.append(url)
        return {"cep": "29101-010", "logradouro": "Rua Itapemirim", "bairro": "Itapuã",
                "localidade": "Vila Velha", "uf": "ES"}

    monkeypatch.setattr(externos, "_get_json", falso)
    resp = client.get("/api/lugares/cep/29101-010", headers=aluno)
    assert resp.status_code == 200
    assert resp.get_json()["endereco"]["bairro"] == "Itapuã"
    # URL fixa do ViaCEP, so com os digitos
    assert chamadas == ["https://viacep.com.br/ws/29101010/json/"]
    # Segunda vez vem do cache
    client.get("/api/lugares/cep/29101010", headers=aluno)
    assert len(chamadas) == 1


def test_cep_invalido_ou_inexistente(client, aluno, monkeypatch):
    assert client.get("/api/lugares/cep/123", headers=aluno).status_code == 400
    monkeypatch.setattr(externos, "_get_json", lambda url: {"erro": "true"})
    assert client.get("/api/lugares/cep/00000000", headers=aluno).status_code == 404


def test_cep_com_api_fora_do_ar(client, aluno):
    # Nos testes as APIs externas estao desligadas: o sistema responde sem quebrar
    resp = client.get("/api/lugares/cep/29101010", headers=aluno)
    assert resp.status_code == 404
    assert "Preencha à mão" in resp.get_json()["error"]


def test_ruas(client, aluno, monkeypatch):
    urls = []

    def falso(url):
        urls.append(url)
        return [
            {"cep": "29101-010", "logradouro": "Rua Itapemirim", "bairro": "Itapuã", "localidade": "Vila Velha", "uf": "ES"},
            {"cep": "29101-011", "logradouro": "Rua Itapemirim", "bairro": "Itapuã", "localidade": "Vila Velha", "uf": "ES"},
        ]

    monkeypatch.setattr(externos, "_get_json", falso)
    resp = client.get("/api/lugares/ruas?q=itape", headers=aluno).get_json()
    assert resp["disponivel"] is True
    assert [r["rua"] for r in resp["ruas"]] == ["Rua Itapemirim"]  # sem repetir a mesma rua/bairro
    assert urls == ["https://viacep.com.br/ws/ES/Vila%20Velha/itape/json/"]


def test_ruas_regras(client, aluno):
    assert client.get("/api/lugares/ruas?q=it", headers=aluno).get_json()["ruas"] == []  # menos de 3 letras
    assert client.get("/api/lugares/ruas?q=itape&cidade=Rio", headers=aluno).status_code == 400
    # API fora: avisa que nao esta disponivel, sem erro
    assert client.get("/api/lugares/ruas?q=itape", headers=aluno).get_json()["disponivel"] is False


def test_get_json_real_falha_sem_quebrar(app, monkeypatch):
    app.config["APIS_EXTERNAS_DESLIGADAS"] = False

    def explode(*args, **kwargs):
        raise OSError("sem internet")

    monkeypatch.setattr(externos.urllib.request, "urlopen", explode)
    assert externos._get_json("https://viacep.com.br/ws/29101010/json/") is None

    class Resposta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(externos.urllib.request, "urlopen",
                        lambda req, timeout: Resposta(json.dumps({"ok": 1}).encode()))
    assert externos._get_json("https://viacep.com.br/ws/29101010/json/") == {"ok": 1}


def test_limite_de_requisicoes(client):
    for _ in range(120):
        assert client.get("/api/lugares/bairros?q=ita").status_code == 200
    resp = client.get("/api/lugares/bairros?q=ita")
    assert resp.status_code == 429
    assert "Muitas requisições" in resp.get_json()["error"]


# ==========================================================
# CAMPO BAIRRO NAO ACEITA ENDERECO
# ==========================================================
@pytest.mark.parametrize("valor", ["Rua Itapemirim", "rua itape", "Av. Hugo Musso", "Avenida Champagnat", "R. Goiânia"])
def test_bairro_que_parece_endereco_e_recusado(client, aluno, valor):
    resp = client.put("/api/auth/me", json={"bairro": valor}, headers=aluno)
    assert resp.status_code == 400
    assert "campo Endereço" in resp.get_json()["campos"]["bairro"]


def test_bairro_normal_e_aceito(client, aluno, nova_carona):
    assert client.put("/api/auth/me", json={"bairro": "Ruas Altas"}, headers=aluno).status_code == 200
    resp = client.post("/api/caronas", json={
        "bairro_origem": "Av. Central", "endereco_origem": "Rua X, 1",
        "data_hora_saida": "2099-01-01T08:00", "vagas": 2,
    }, headers=aluno)
    assert resp.status_code == 400
    assert "bairro_origem" in resp.get_json()["campos"]


def test_busca_de_carona_ignora_acento(client, novo_aluno, nova_carona):
    _, motorista = novo_aluno("5", "Motorista")
    nova_carona(motorista, bairro_origem="Gloria")
    _, ana = novo_aluno("6", "Ana")
    assert len(client.get("/api/caronas?bairro=Glória", headers=ana).get_json()["caronas"]) == 1
    assert len(client.get("/api/caronas?bairro=GLOR", headers=ana).get_json()["caronas"]) == 1
    assert client.get("/api/caronas?bairro=Ibes", headers=ana).get_json()["caronas"] == []


# ==========================================================
# ONIBUS (estimativa, sem horario oficial)
# ==========================================================
def test_onibus_do_bairro_ate_a_uvv(client, aluno):
    resp = client.get("/api/lugares/onibus?bairro=gloria&sentido=ida&hora=7", headers=aluno).get_json()
    assert resp["estimativa"] is True
    assert "ÔnibusGV" in resp["aviso"]
    assert resp["link_oficial"].startswith("https://")
    assert resp["terminal_troca"] == "T. Ibes"                      # a 607 (Gloria/Terminal Ibes) leva ao Ibes
    assert "607" in [linha["numero"] for linha in resp["linhas_do_bairro"]]
    assert [linha["numero"] for linha in resp["linhas_ate_uvv"]] == ["608", "606", "1721"]
    assert "horário" not in resp["caminho"]                          # nunca inventa horario


def test_onibus_a_noite_so_linhas_noturnas(client, aluno):
    resp = client.get("/api/lugares/onibus?bairro=Praia da Costa&sentido=volta&hora=23", headers=aluno).get_json()
    assert [linha["numero"] for linha in resp["linhas_ate_uvv"]] == ["664"]
    assert "noturnas" in resp["caminho"]
    assert resp["caminho"].startswith("Da UVV")


def test_onibus_bairro_perto_sugere_ir_a_pe(client, aluno):
    resp = client.get("/api/lugares/onibus?bairro=Boa Vista", headers=aluno).get_json()
    assert "a pé" in resp["caminho"]
    assert resp["terminal_troca"] is None


def test_onibus_validacoes(client, aluno):
    assert client.get("/api/lugares/onibus?bairro=Inventado", headers=aluno).status_code == 404
    assert client.get("/api/lugares/onibus?bairro=Ibes&sentido=x", headers=aluno).status_code == 400
    assert client.get("/api/lugares/onibus?bairro=Ibes&hora=25", headers=aluno).status_code == 400
    assert client.get("/api/lugares/onibus?bairro=Ibes").status_code == 401
