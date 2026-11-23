"""Calculo do rateio pelo combustivel: conta, energias, metros, adicional, teto, transito e o que o servidor salva."""
from datetime import datetime
from decimal import Decimal

import pytest

from caronauvv.admin.models import Configuracao
from caronauvv.caronas.combustivel import CONSUMO_MEDIO, calcular_rateio, horario_de_pico
from caronauvv.errors import ApiError
from caronauvv.ext.db import db

FORA_DO_PICO = "2099-01-04T10:00"   # domingo de manha: sem acrescimo de transito


# ==========================================================
# A CONTA (funcao pura, precos padrao: gasolina 6,29 | etanol 4,39 | diesel 6,19 | kWh 0,89)
# ==========================================================
def test_conta_completa_com_gasolina(app):
    # 6,2 km / 12,5 km/l = 0,496 L x R$ 6,29 = R$ 3,12 da viagem; 4 ocupantes (3 vagas + motorista)
    r = calcular_rateio(6.2, 3, "flex", 12.5, "0.22")
    assert r.distancia_m == 6200
    assert r.unidade == "L"
    assert r.quantidade == Decimal("0.496")
    assert r.preco_unidade == Decimal("6.29")
    assert r.custo_total == Decimal("3.12")
    assert r.ocupantes == 4
    assert r.combustivel_por_pessoa == Decimal("0.78")
    assert r.adicional == Decimal("0.22")
    assert r.valor_por_passageiro == Decimal("1.00")
    assert r.consumo_estimado is False


def test_distancia_com_precisao_de_metro(app):
    # 6,2004 km arredonda para 6.200 m; 6,2006 km para 6.201 m
    assert calcular_rateio(6.2004, 3, "flex", 12.5).distancia_m == 6200
    assert calcular_rateio(6.2006, 3, "flex", 12.5).distancia_m == 6201
    # aceita virgula como separador decimal
    assert calcular_rateio("6,2", 3, "flex", "12,5").distancia_m == 6200


@pytest.mark.parametrize("energia, preco, unidade", [
    ("gasolina", "6.29", "L"), ("flex", "6.29", "L"), ("hibrido", "6.29", "L"),
    ("etanol", "4.39", "L"), ("diesel", "6.19", "L"), ("eletrico", "0.89", "kWh"),
])
def test_cada_energia_usa_o_proprio_preco(app, energia, preco, unidade):
    r = calcular_rateio(10, 1, energia, 10)   # 10 km a 10 km/l (ou kWh) = 1 unidade
    assert r.quantidade == Decimal("1.000")
    assert r.unidade == unidade
    assert r.preco_unidade == Decimal(preco)
    assert r.custo_total == Decimal(preco)
    assert r.combustivel_por_pessoa == (Decimal(preco) / 2).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def test_eletrico_e_hibrido_saem_mais_baratos(app):
    gasolina = calcular_rateio(17, 3, "gasolina", 11)
    hibrido = calcular_rateio(17, 3, "hibrido", 18)
    eletrico = calcular_rateio(17, 3, "eletrico", 7)
    assert eletrico.combustivel_por_pessoa < hibrido.combustivel_por_pessoa < gasolina.combustivel_por_pessoa


def test_sem_consumo_usa_a_media_e_avisa(app):
    r = calcular_rateio(10, 1, "eletrico", None)
    assert r.consumo_estimado is True
    assert r.consumo_km == Decimal(str(CONSUMO_MEDIO["eletrico"]))


def test_preco_vem_do_painel(app):
    db.session.add(Configuracao(chave="preco_gasolina", valor="7.00"))
    db.session.commit()
    assert calcular_rateio(10, 1, "gasolina", 10).preco_unidade == Decimal("7.00")


@pytest.mark.parametrize("args, campo", [
    ((0, 3, "flex", 12), "distancia_km"),
    ((600, 3, "flex", 12), "distancia_km"),
    (("abc", 3, "flex", 12), "distancia_km"),
    ((10, 3, "flex", 0.0), None),            # 0 = "sem consumo": usa a media (nao e erro)
    ((10, 3, "flex", 80), "consumo_km"),
    ((10, 3, "carvao", 12), "energia"),
    ((10, 9, "flex", 12), "vagas"),
])
def test_dados_invalidos(app, args, campo):
    if campo is None:
        assert calcular_rateio(*args).consumo_estimado is True
        return
    with pytest.raises(ApiError) as erro:
        calcular_rateio(*args)
    assert campo in erro.value.campos


def test_adicional_negativo(app):
    with pytest.raises(ApiError):
        calcular_rateio(10, 1, "flex", 10, "-1")


# ==========================================================
# API: valor sugerido com a conta aberta
# ==========================================================
def test_valor_sugerido_mostra_a_conta(client, novo_aluno):
    _, h = novo_aluno(1)
    resp = client.get("/api/caronas/valor-sugerido?distancia_km=6.2&vagas=3&energia=flex&consumo_km=12.5&adicional=0.22",
                      headers=h).get_json()
    assert resp["valor_sugerido"] == 1.0
    calculo = resp["calculo"]
    assert calculo["distancia_m"] == 6200
    assert calculo["quantidade"] == 0.496
    assert calculo["combustivel_por_pessoa"] == 0.78
    assert calculo["adicional"] == 0.22
    assert calculo["energia_nome"] == "Flex (gasolina)"
    assert resp["acima_do_teto"] is False


def test_valor_sugerido_avisa_quando_passa_do_teto(client, novo_aluno):
    _, h = novo_aluno(1)
    resp = client.get("/api/caronas/valor-sugerido?distancia_km=100&vagas=1&energia=gasolina&consumo_km=8",
                      headers=h).get_json()
    assert resp["acima_do_teto"] is True


# ==========================================================
# CARONA: o servidor calcula e guarda o detalhamento
# ==========================================================
def _carro(client, h, **extra):
    corpo = {"modelo": "Kwid", "cor": "Azul", "placa": "ELE1A23", "energia": "eletrico", "consumo_km": 7, **extra}
    resp = client.post("/api/veiculos", json=corpo, headers=h)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["veiculo"]


def test_carro_guarda_energia_e_consumo(client, novo_aluno):
    _, h = novo_aluno(1)
    carro = _carro(client, h)
    assert carro["energia"] == "eletrico" and carro["consumo_km"] == 7
    assert client.post("/api/veiculos", json={"modelo": "X", "cor": "Y", "placa": "AAA1A11", "energia": "vapor"},
                       headers=h).status_code == 400
    # sem informar: entra como flex, sem consumo
    padrao = client.post("/api/veiculos", json={"modelo": "Gol", "cor": "Prata", "placa": "BBB2B22"},
                         headers=h).get_json()["veiculo"]
    assert padrao["energia"] == "flex" and padrao["consumo_km"] is None


def test_carona_calculada_ignora_o_valor_do_navegador(client, novo_aluno, nova_carona):
    _, h = novo_aluno(1)
    carro = _carro(client, h)
    # o navegador manda R$ 4,99, mas com o adicional ligado o servidor faz a conta
    carona = nova_carona(h, veiculo_id=carro["id"], distancia_km=5, vagas=2,
                         adicional_por_passageiro="0.79", valor_por_passageiro="4.99", data_hora_saida=FORA_DO_PICO)
    # 5 km / 7 km/kWh = 0,714 kWh x R$ 0,89 = R$ 0,64 / 3 ocupantes = R$ 0,21 + R$ 0,79
    assert carona["valor_por_passageiro"] == 1.0
    assert carona["rateio"] == {"energia": "eletrico", "consumo_km": 7.0, "combustivel": 0.21, "adicional": 0.79,
                                "transito_percentual": 0, "trechos_transito": []}


def test_teto_vale_para_combustivel_mais_adicional(client, novo_aluno):
    _, h = novo_aluno(1)
    carro = _carro(client, h, energia="gasolina", consumo_km=10, placa="GAS1A23")
    # 20 km / 10 km/l = 2 L x R$ 6,29 = R$ 12,58 / 2 ocupantes = R$ 6,29 + R$ 0,50: passa do teto de R$ 5,00
    resp = client.post("/api/caronas", json={
        "bairro_origem": "Serra", "endereco_origem": "Rua A", "vagas": 1, "veiculo_id": carro["id"],
        "data_hora_saida": "2099-01-01T10:00", "distancia_km": 20, "adicional_por_passageiro": "0.50",
    }, headers=h)
    assert resp.status_code == 400
    assert "adicional_por_passageiro" in resp.get_json()["campos"]


def test_editar_vagas_recalcula(client, novo_aluno, nova_carona):
    _, h = novo_aluno(1)
    carro = _carro(client, h)
    carona = nova_carona(h, veiculo_id=carro["id"], distancia_km=5, vagas=2, adicional_por_passageiro="0.79", data_hora_saida=FORA_DO_PICO)
    editada = client.put(f"/api/caronas/{carona['id']}", json={"vagas": 4}, headers=h).get_json()["carona"]
    # 0,64 / 5 ocupantes = R$ 0,13 de energia; o adicional continua R$ 0,79
    assert editada["rateio"]["combustivel"] == 0.13
    assert editada["rateio"]["adicional"] == 0.79
    assert editada["valor_por_passageiro"] == 0.92


def test_valor_digitado_a_mao_tira_o_detalhamento(client, novo_aluno, nova_carona):
    _, h = novo_aluno(1)
    carro = _carro(client, h)
    carona = nova_carona(h, veiculo_id=carro["id"], distancia_km=5, vagas=2, adicional_por_passageiro="0.79", data_hora_saida=FORA_DO_PICO)
    editada = client.put(f"/api/caronas/{carona['id']}", json={"valor_por_passageiro": "2.00"}, headers=h).get_json()["carona"]
    assert editada["valor_por_passageiro"] == 2.0
    assert editada["rateio"] is None


def test_calculo_sem_distancia_e_recusado(client, novo_aluno):
    _, h = novo_aluno(1)
    resp = client.post("/api/caronas", json={
        "bairro_origem": "Itapua", "endereco_origem": "Rua A", "vagas": 2,
        "data_hora_saida": "2099-01-01T10:00", "adicional_por_passageiro": "0.50",
    }, headers=h)
    assert resp.status_code == 400
    assert "distancia_km" in resp.get_json()["campos"]


def test_carona_sem_carro_usa_flex_com_consumo_medio(client, novo_aluno, nova_carona):
    _, h = novo_aluno(1)
    carona = nova_carona(h, distancia_km=12, vagas=3, adicional_por_passageiro="0", data_hora_saida=FORA_DO_PICO)
    # 12 km / 12 km/l (media flex) = 1 L x 6,29 / 4 = R$ 1,57
    assert carona["rateio"]["energia"] == "flex"
    assert carona["rateio"]["combustivel"] == 1.57


# ==========================================================
# TRANSITO DA GRANDE VITORIA (horario de pico e trechos criticos)
# ==========================================================
SEGUNDA_7H = datetime(2099, 1, 5, 7, 0)     # segunda-feira, pico da manha
SEGUNDA_10H = datetime(2099, 1, 5, 10, 0)
SEXTA_18H = datetime(2099, 1, 9, 18, 0)     # pico da tarde
SABADO_7H = datetime(2099, 1, 3, 7, 0)


def test_horario_de_pico():
    assert horario_de_pico(SEGUNDA_7H) and horario_de_pico(SEXTA_18H)
    assert not horario_de_pico(SEGUNDA_10H)
    assert not horario_de_pico(SABADO_7H)          # fim de semana nao tem pico
    assert not horario_de_pico(datetime(2099, 1, 5, 8, 30))   # 8h30 ja saiu do pico
    assert not horario_de_pico(None)


def test_pico_aumenta_o_consumo_em_25_por_cento(app):
    normal = calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_10H)
    pico = calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_7H)
    assert normal.transito_percentual == 0 and normal.quantidade == Decimal("1.000")
    assert pico.transito_percentual == 25
    assert pico.quantidade == Decimal("1.250")
    assert pico.quantidade_sem_transito == Decimal("1.000")
    assert pico.transito_motivos == ["+25% por trânsito no horário de pico"]
    assert pico.custo_total > normal.custo_total


def test_trechos_criticos_somam_ate_o_maximo(app):
    r = calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_7H, trechos=["terceira_ponte", "terceira_ponte"])
    assert r.transito_percentual == 35                       # 25 + 10 (trecho repetido conta 1 vez)
    assert "+10% pela Terceira Ponte" in r.transito_motivos
    r = calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_7H,
                        trechos=["terceira_ponte", "segunda_ponte", "rodovia_do_sol", "br101_carapina", "inventado"])
    assert r.transito_percentual == 50                       # limitado
    assert r.transito_motivos[-1] == "limitado a +50%"
    # Fora do pico os trechos nao pesam
    assert calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_10H, trechos=["terceira_ponte"]).transito_percentual == 0


def test_percentuais_do_transito_vem_do_painel(app):
    db.session.add(Configuracao(chave="transito_pico_percentual", valor="40"))
    db.session.commit()
    assert calcular_rateio(10, 3, "gasolina", 10, saida=SEGUNDA_7H).transito_percentual == 40


def test_valor_sugerido_com_transito(client, novo_aluno):
    _, h = novo_aluno(1)
    url = "/api/caronas/valor-sugerido?distancia_km=10&vagas=3&energia=gasolina&consumo_km=10"
    conta = client.get(f"{url}&data_hora=2099-01-05T07:00&trechos=terceira_ponte", headers=h).get_json()["calculo"]
    assert conta["transito_percentual"] == 35
    assert client.get(f"{url}&data_hora=ontem", headers=h).status_code == 400


def test_carona_guarda_o_transito_e_recalcula_ao_mudar_o_horario(client, novo_aluno, nova_carona):
    _, h = novo_aluno(1)
    carona = nova_carona(h, distancia_km=10, vagas=3, adicional_por_passageiro="0", data_hora_saida="2099-01-05T07:00",
                         trechos_transito=["terceira_ponte"])
    assert carona["rateio"]["transito_percentual"] == 35
    assert carona["rateio"]["trechos_transito"] == ["terceira_ponte"]
    pico = carona["valor_por_passageiro"]
    editada = client.put(f"/api/caronas/{carona['id']}", json={"data_hora_saida": "2099-01-05T10:00"}, headers=h).get_json()["carona"]
    assert editada["rateio"]["transito_percentual"] == 0
    assert editada["valor_por_passageiro"] < pico
    resp = client.put(f"/api/caronas/{carona['id']}", json={"trechos_transito": ["ponte_inventada"]}, headers=h)
    assert resp.status_code == 400
