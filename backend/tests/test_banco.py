from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from caronauvv.admin.models import Configuracao
from caronauvv.auth.models import Usuario, Veiculo
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.avaliacoes.services import gerar_pix_copia_cola
from caronauvv.caronas.models import Carona, PosicaoGps, Solicitacao
from caronauvv.ext.db import db, limpar_trilhas_gps
from caronauvv.ext.db.seed import popular_banco


def contar(modelo) -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(modelo))


@pytest.fixture
def populado(app):
    popular_banco()
    return app


# ==========================================================
# INTEGRIDADE (FK ligada no SQLite, CHECKs de status)
# ==========================================================
def test_chave_estrangeira_e_verificada(app):
    db.session.add(Veiculo(usuario_id=999, modelo="HB20", cor="Branco", placa="AAA1A11"))
    with pytest.raises(IntegrityError):
        db.session.commit()


@pytest.mark.parametrize("campo, valor", [
    ("status", "voando"), ("sentido", "lado"), ("vagas", 7), ("valor_por_passageiro", -1),
])
def test_check_constraints_da_carona(populado, campo, valor):
    with pytest.raises(IntegrityError):
        db.session.execute(db.update(Carona).where(Carona.id == 1).values({campo: valor}))


def test_status_de_solicitacao_invalido(populado):
    with pytest.raises(IntegrityError):
        db.session.execute(db.update(Solicitacao).where(Solicitacao.id == 1).values(status="talvez"))


def test_ninguem_se_autoavalia(populado):
    kaua = db.session.scalar(db.select(Usuario).where(Usuario.matricula == "202416377"))
    db.session.add(Avaliacao(solicitacao_id=1, avaliador=kaua, avaliado=kaua, nota=5))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_apagar_veiculo_deixa_carona_sem_veiculo(populado):
    db.session.execute(db.delete(Veiculo).where(Veiculo.placa == "KAU2B34"))
    db.session.commit()
    assert db.session.scalar(db.select(db.func.count()).where(Carona.veiculo_id.is_(None))) >= 2


def test_apagar_carona_apaga_pedidos_e_gps(populado):
    db.session.execute(db.delete(Carona).where(Carona.status == "concluida"))
    db.session.commit()
    assert contar(PosicaoGps) == 0
    assert db.session.scalar(db.select(db.func.count()).where(Solicitacao.faltou)) == 0


# ==========================================================
# SEED
# ==========================================================
def test_seed_preenche_todas_as_tabelas(populado):
    vazias = [
        nome for nome, tabela in db.metadata.tables.items()
        if db.session.scalar(db.select(db.func.count()).select_from(tabela)) == 0
    ]
    assert len(db.metadata.tables) == 18
    assert vazias == []


def test_seed_nao_duplica(populado):
    usuarios, configs = contar(Usuario), contar(Configuracao)
    popular_banco()
    assert (contar(Usuario), contar(Configuracao)) == (usuarios, configs)


def test_seed_respeita_vagas(populado):
    for carona in db.session.scalars(db.select(Carona)):
        assert carona.vagas_restantes >= 0


# ==========================================================
# CONFIGURACOES E MANUTENCAO
# ==========================================================
def test_configuracao_usa_banco_e_cai_no_padrao(app):
    assert Configuracao.obter_int("dias_guardar_gps", 0) == 30          # PADROES
    assert Configuracao.obter("chave_que_nao_existe", "x") == "x"
    db.session.add(Configuracao(chave="dias_guardar_gps", valor="10"))
    db.session.commit()
    assert Configuracao.obter_int("dias_guardar_gps", 0) == 10          # banco


def test_limpar_trilhas_gps(populado):
    carona = db.session.get(Carona, 1)
    db.session.add(PosicaoGps(carona=carona, lat=0, lng=0,
                              registrada_em=datetime.now() - timedelta(days=31)))
    db.session.commit()
    antes = contar(PosicaoGps)
    assert limpar_trilhas_gps() == 1
    assert contar(PosicaoGps) == antes - 1


# ==========================================================
# PIX
# ==========================================================
def test_pix_exemplo_oficial_do_banco_central():
    # Exemplo do Manual do BR Code (chave aleatoria, sem valor)
    esperado = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000"
                "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D")
    assert gerar_pix_copia_cola("123e4567-e12b-12d1-a456-426655440000",
                                "Fulano de Tal", "BRASILIA") == esperado


def test_pix_com_valor_e_acentos():
    codigo = gerar_pix_copia_cola("kaua@uvv.br", "Kauã Araujo", "Vila Velha", 1)
    assert "54041.00" in codigo
    assert "5911Kaua Araujo" in codigo
    assert codigo.startswith("000201") and len(codigo.split("6304")[-1]) == 4
