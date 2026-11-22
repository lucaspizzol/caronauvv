from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from caronauvv.ext.db import db
from caronauvv.auth.models import Usuario, Veiculo
from caronauvv.caronas.models import Carona, Solicitacao


def novo_usuario(matricula, nome, bairro="Itapua"):
    u = Usuario(matricula=matricula, email=f"{matricula}@uvv.br", nome=nome,
                telefone="27999990000", bairro=bairro)
    u.set_senha("123456")
    db.session.add(u)
    return u


def test_cria_todas_as_tabelas(app):
    tabelas = set(db.metadata.tables)
    assert {"usuarios", "veiculos", "caronas", "solicitacoes", "avaliacoes",
            "pagamentos", "notificacoes", "alertas", "denuncias"} <= tabelas


def test_senha_com_hash(app):
    u = novo_usuario("202416377", "Kaua")
    db.session.commit()
    assert u.senha_hash != "123456"
    assert u.check_senha("123456")


def test_vagas_restantes(app):
    motorista = novo_usuario("1", "Kaua")
    p1, p2 = novo_usuario("2", "Ana"), novo_usuario("3", "Pedro")
    carro = Veiculo(dono=motorista, modelo="HB20", cor="Branco", placa="KAU2B34")
    carona = Carona(motorista=motorista, veiculo=carro, bairro_origem="Itapua",
                    endereco_origem="Rua Itaunas, 120",
                    data_hora_saida=datetime.now() + timedelta(hours=2),
                    vagas=2, valor_por_passageiro=1.00)
    db.session.add_all([
        carona,
        Solicitacao(carona=carona, passageiro=p1, status="aceita"),
        Solicitacao(carona=carona, passageiro=p2, status="pendente"),
    ])
    db.session.commit()
    assert carona.vagas_restantes == 1


def test_nao_pode_pedir_mesma_carona_duas_vezes(app):
    motorista, p = novo_usuario("1", "Kaua"), novo_usuario("2", "Ana")
    carona = Carona(motorista=motorista, bairro_origem="Itapua", endereco_origem="Rua X",
                    data_hora_saida=datetime.now() + timedelta(hours=2), vagas=2)
    db.session.add_all([carona, Solicitacao(carona=carona, passageiro=p),
                        Solicitacao(carona=carona, passageiro=p)])
    with pytest.raises(IntegrityError):
        db.session.commit()
