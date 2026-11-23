"""Acabamento do painel: historico das acoes da administracao, exportar CSV e grafico de caronas por dia."""
import csv
import io
from datetime import date, datetime, timedelta

from caronauvv.admin.models import AcaoAdmin, Configuracao
from caronauvv.auth.models import Documento, Usuario
from caronauvv.avaliacoes.models import Avaliacao
from caronauvv.ext.db import db
from caronauvv.ext.db.seed import popular_banco
from caronauvv.seguranca.models import Alerta, Denuncia


def admin_do_seed(client):
    """Banco de exemplo + login com admin@uvv.br."""
    popular_banco()
    token = client.post("/api/auth/login", json={"login": "admin@uvv.br", "senha": "123456"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def acoes(acao=None):
    consulta = db.select(AcaoAdmin).order_by(AcaoAdmin.id)
    if acao:
        consulta = consulta.where(AcaoAdmin.acao == acao)
    return list(db.session.scalars(consulta))


def ler_csv(resp) -> list[list[str]]:
    texto = resp.get_data().decode("utf-8")
    assert texto.startswith("﻿")                 # BOM: o Excel abre com acentos
    return list(csv.reader(io.StringIO(texto[1:]), delimiter=";"))


# ==========================================================
# HISTORICO: cada acao do admin fica registrada
# ==========================================================
def test_aprovar_e_recusar_selo_ficam_no_historico(client, novo_aluno, admin):
    aluno, _ = novo_aluno("1", "Marina Costa")
    client.post(f"/api/admin/usuarios/{aluno['id']}/verificar", json={"aprovado": True}, headers=admin[1])
    client.post(f"/api/admin/usuarios/{aluno['id']}/verificar", json={"aprovado": False}, headers=admin[1])
    aprovou, recusou = acoes()
    assert (aprovou.acao, recusou.acao) == ("aprovar_selo", "recusar_selo")
    assert aprovou.admin_id == admin[0]["id"]
    assert (aprovou.alvo_id, aprovou.alvo_nome) == (aluno["id"], "Marina Costa")


def test_suspender_e_reativar_ficam_no_historico(client, novo_aluno, admin):
    aluno, _ = novo_aluno("1", "Pedro Lima")
    url = f"/api/admin/usuarios/{aluno['id']}/suspender"
    client.post(url, json={"ativo": False}, headers=admin[1])
    client.post(url, json={"ativo": False}, headers=admin[1])   # repetir nao duplica
    client.post(url, json={"ativo": True}, headers=admin[1])
    assert [a.acao for a in acoes()] == ["suspender", "reativar"]
    assert "Suspenso(a) pela administração" in acoes("reativar")[0].detalhe


def test_mudar_regras_registra_so_o_que_mudou(client, admin):
    client.put("/api/admin/configuracoes", json={"media_minima_usuario": "3", "nota_alerta_avaliacao": "4.5"},
               headers=admin[1])
    [mudanca] = acoes("alterar_regras")
    assert mudanca.detalhe == "nota_alerta_avaliacao: 4 → 4.5"   # a media continuou 3: nao aparece
    client.put("/api/admin/configuracoes", json={"nota_alerta_avaliacao": "4.5"}, headers=admin[1])
    assert len(acoes("alterar_regras")) == 1                     # salvar sem mudar nada nao registra


def test_resolver_alerta_fica_no_historico(client, viagem, admin):
    db.session.add(Alerta(carona_id=viagem["carona"]["id"], usuario_id=viagem["passageiro"]["id"],
                          tipo="botao_panico", detalhe="Teste"))
    db.session.commit()
    alerta = db.session.scalar(db.select(Alerta))
    client.post(f"/api/admin/alertas/{alerta.id}/resolver", headers=admin[1])
    client.post(f"/api/admin/alertas/{alerta.id}/resolver", headers=admin[1])  # ja resolvido: nao repete
    [registro] = acoes("resolver_alerta")
    assert registro.alvo_id == viagem["passageiro"]["id"]
    assert "botao panico" in registro.detalhe


def test_documento_denuncia_e_2fa_ficam_no_historico(client):
    h = admin_do_seed(client)
    marina = db.session.scalar(db.select(Usuario).where(Usuario.email == "marina@uvv.br"))
    beatriz = db.session.scalar(db.select(Usuario).where(Usuario.email == "beatriz@uvv.br"))
    doc = db.session.scalar(db.select(Documento).where(Documento.usuario_id == marina.id))
    denuncia = db.session.scalar(db.select(Denuncia))

    client.post(f"/api/admin/documentos/{doc.id}/analisar", json={"aprovado": False, "motivo": "Foto cortada."}, headers=h)
    client.post(f"/api/admin/denuncias/{denuncia.id}", json={"status": "encerrada", "resolucao": "Conversamos com o aluno."},
                headers=h)
    client.post(f"/api/admin/usuarios/{beatriz.id}/resetar-2fa", headers=h)

    [doc_recusado] = [a for a in acoes("recusar_documento") if a.alvo_id == marina.id]
    assert doc_recusado.detalhe == "identidade: Foto cortada."
    [encerrou] = acoes("encerrar_denuncia")
    assert encerrou.alvo_nome == "Pedro Lima" and "Conversamos" in encerrou.detalhe
    assert acoes("resetar_2fa")[0].alvo_id == beatriz.id


def test_exclusao_automatica_entra_como_acao_do_sistema(client, concluida, admin):
    resp = client.post(f"/api/solicitacoes/{concluida['sid']}/avaliacao", json={"nota": 1},
                       headers=concluida["h_motorista"])
    assert resp.status_code == 201
    [registro] = acoes("exclusao_automatica")
    assert registro.admin_id is None                              # ninguem clicou: foi a regra
    assert registro.alvo_id == concluida["passageiro"]["id"]
    item = client.get("/api/admin/historico", headers=admin[1]).get_json()["acoes"][0]
    assert item["admin"] is None and item["acao"] == "exclusao_automatica"


def test_acao_que_falha_nao_deixa_registro(client, novo_aluno, admin):
    # suspender a propria conta e proibido: nada pode ficar no historico
    resp = client.post(f"/api/admin/usuarios/{admin[0]['id']}/suspender", json={"ativo": False}, headers=admin[1])
    assert resp.status_code == 400
    assert acoes() == []


# ==========================================================
# HISTORICO: rota do painel
# ==========================================================
def test_historico_mais_recente_primeiro_e_filtro(client):
    h = admin_do_seed(client)
    corpo = client.get("/api/admin/historico", headers=h).get_json()
    assert "exportar_dados" in corpo["tipos"]
    datas = [a["criado_em"] for a in corpo["acoes"]]
    assert datas == sorted(datas, reverse=True) and len(datas) >= 7
    so_selo = client.get("/api/admin/historico?acao=aprovar_selo", headers=h).get_json()["acoes"]
    assert {a["acao"] for a in so_selo} == {"aprovar_selo"}
    assert so_selo[0]["admin"]["nome"] == "Administrador CaronaUVV"


def test_historico_respeita_o_periodo(client, admin):
    db.session.add(AcaoAdmin(admin_id=admin[0]["id"], acao="aprovar_selo",
                             created_at=datetime.now() - timedelta(days=40)))
    db.session.commit()
    assert client.get("/api/admin/historico?dias=30", headers=admin[1]).get_json()["acoes"] == []
    assert len(client.get("/api/admin/historico?dias=60", headers=admin[1]).get_json()["acoes"]) == 1


def test_historico_recusa_acao_desconhecida(client, admin):
    assert client.get("/api/admin/historico?acao=apagar_tudo", headers=admin[1]).status_code == 400


def test_aluno_nao_ve_historico_nem_exporta(client, novo_aluno):
    _, h = novo_aluno("1", "Ana")
    assert client.get("/api/admin/historico", headers=h).status_code == 403
    assert client.get("/api/admin/exportar/usuarios", headers=h).status_code == 403
    assert client.get("/api/admin/exportar/usuarios").status_code == 401


# ==========================================================
# EXPORTAR CSV
# ==========================================================
def test_exportar_usuarios(client):
    h = admin_do_seed(client)
    resp = client.get("/api/admin/exportar/usuarios", headers=h)
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert resp.headers["Content-Disposition"] == f'attachment; filename="caronauvv_usuarios_{date.today():%Y-%m-%d}.csv"'
    assert resp.headers["Cache-Control"] == "no-store"
    linhas = ler_csv(resp)
    cabecalho = linhas[0]
    assert cabecalho[:4] == ["ID", "Nome", "E-mail", "Matrícula"]
    # LGPD: nada de telefone, chave Pix ou senha no relatorio
    assert not any(c in " ".join(cabecalho) for c in ("Telefone", "Pix", "Senha"))
    assert len(linhas) - 1 == db.session.scalar(db.select(db.func.count()).select_from(Usuario))
    pedro = next(l for l in linhas if l[1] == "Pedro Lima")
    assert pedro[cabecalho.index("Média recebida")] == "3,00"        # virgula decimal (Excel em portugues)
    assert pedro[cabecalho.index("Conta")] == "Ativa"


def test_exportar_avaliacoes_e_viagens(client):
    h = admin_do_seed(client)
    avaliacoes = ler_csv(client.get("/api/admin/exportar/avaliacoes", headers=h))
    assert len(avaliacoes) - 1 == db.session.scalar(db.select(db.func.count()).select_from(Avaliacao))
    assert avaliacoes[0][avaliacoes[0].index("Nota")] == "Nota"
    viagens = ler_csv(client.get("/api/admin/exportar/viagens", headers=h))
    situacoes = {l[viagens[0].index("Situação")] for l in viagens[1:]}
    assert {"Concluída", "Em andamento"} <= situacoes
    # ida: bairro -> UVV
    assert any(t.endswith("→ UVV - Entrada principal") for t in (l[viagens[0].index("Trecho")] for l in viagens[1:]))


def test_exportar_fica_no_historico(client):
    h = admin_do_seed(client)
    antes = len(acoes("exportar_dados"))
    client.get("/api/admin/exportar/viagens", headers=h)
    assert len(acoes("exportar_dados")) == antes + 1
    assert acoes("exportar_dados")[-1].detalhe.startswith("Viagens: ")


def test_exportar_relatorio_desconhecido(client, admin):
    assert client.get("/api/admin/exportar/senhas", headers=admin[1]).status_code == 404


def test_csv_neutraliza_formula_escrita_por_aluno(client, concluida, admin):
    # comentario malicioso: no Excel, "=..." viraria formula
    client.post(f"/api/solicitacoes/{concluida['sid']}/avaliacao",
                json={"nota": 5, "comentario": "=HYPERLINK(\"http://x\";\"clique\")"}, headers=concluida["h_passageiro"])
    linhas = ler_csv(client.get("/api/admin/exportar/avaliacoes", headers=admin[1]))
    comentario = linhas[1][linhas[0].index("Comentário")]
    assert comentario.startswith("'=")


# ==========================================================
# GRAFICO: caronas por dia (visao geral)
# ==========================================================
def test_resumo_traz_caronas_dos_ultimos_30_dias(client):
    h = admin_do_seed(client)
    dias = client.get("/api/admin/resumo", headers=h).get_json()["resumo"]["caronas_por_dia"]
    assert len(dias) == 30
    assert dias[-1]["dia"] == date.today().isoformat()
    assert dias[0]["dia"] == (date.today() - timedelta(days=29)).isoformat()
    assert all(d["total"] == d["concluidas"] + d["canceladas"] + d["outras"] for d in dias)
    assert sum(d["concluidas"] for d in dias) >= 4                     # as concluidas do seed


def test_grafico_nao_conta_carona_futura_nem_antiga(client, viagem, admin):
    from caronauvv.caronas.models import Carona

    carona = db.session.get(Carona, viagem["carona"]["id"])
    carona.data_hora_saida = datetime.now() + timedelta(days=2)
    db.session.commit()
    dias = client.get("/api/admin/resumo", headers=admin[1]).get_json()["resumo"]["caronas_por_dia"]
    assert sum(d["total"] for d in dias) == 0
    carona.data_hora_saida = datetime.now() - timedelta(days=45)
    db.session.commit()
    dias = client.get("/api/admin/resumo", headers=admin[1]).get_json()["resumo"]["caronas_por_dia"]
    assert sum(d["total"] for d in dias) == 0


def test_configuracao_nova_conta_mudanca_a_partir_do_padrao(client, admin):
    assert db.session.get(Configuracao, "preco_kwh") is None
    client.put("/api/admin/configuracoes", json={"preco_kwh": "0.95"}, headers=admin[1])
    assert acoes("alterar_regras")[0].detalhe == "preco_kwh: 0.89 → 0.95"
