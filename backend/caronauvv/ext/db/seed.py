"""
Dados iniciais do CaronaUVV (uso: flask --app app.py seed-db).

- Configuracoes padrao ("Regras e precos"): sempre inseridas se faltarem.
- Dados de exemplo (usuarios, caronas, pedidos...): so se o banco estiver vazio.
  Todos os usuarios de exemplo tem a senha 123456.
"""
from datetime import date, datetime, time, timedelta

from caronauvv.admin.models import Busca, Configuracao
from caronauvv.auth.models import ContatoConfianca, Usuario, Veiculo
from caronauvv.avaliacoes.models import Avaliacao, AvaliacaoTag, Pagamento
from caronauvv.avaliacoes.services import gerar_pix_copia_cola
from caronauvv.caronas.models import Carona, PosicaoGps, Solicitacao
from caronauvv.notificacoes.models import Notificacao
from caronauvv.seguranca.models import Alerta, Denuncia, LinkCompartilhado

from . import db

SENHA_EXEMPLO = "123456"

# Coordenadas aproximadas (Vila Velha - ES)
UVV = (-20.3617, -40.3075)
ITAPUA = (-20.3477, -40.2949)
PRAIA_DA_COSTA = (-20.3330, -40.2840)


def popular_banco() -> str:
    novas = _configuracoes_padrao()
    if db.session.scalar(db.select(Usuario).limit(1)) is not None:
        db.session.commit()
        return f"{novas} configuracoes inseridas; ja existem usuarios, dados de exemplo nao foram criados."

    _dados_de_exemplo()
    db.session.commit()
    return f"{novas} configuracoes inseridas e dados de exemplo criados (senha de todos: {SENHA_EXEMPLO})."


# ==========================================================
# CONFIGURACOES ("Regras e precos")
# ==========================================================
def _configuracoes_padrao() -> int:
    novas = 0
    for chave, (valor, descricao) in Configuracao.PADROES.items():
        if db.session.get(Configuracao, chave) is None:
            db.session.add(Configuracao(chave=chave, valor=valor, descricao=descricao))
            novas += 1
    return novas


def _usuario(matricula, email, nome, bairro, **extra) -> Usuario:
    extra.setdefault("email_verificado", True)  # contas de exemplo ja confirmaram o e-mail UVV
    u = Usuario(matricula=matricula, email=email, nome=nome, bairro=bairro,
                telefone=extra.pop("telefone", "27999990000"), **extra)
    u.set_senha(SENHA_EXEMPLO)
    db.session.add(u)
    return u


# ==========================================================
# DADOS DE EXEMPLO (cenas das telas do design)
# ==========================================================
def _dados_de_exemplo() -> None:
    hoje = date.today()
    amanha, ontem = hoje + timedelta(days=1), hoje - timedelta(days=1)
    as_ = lambda dia, h, m=0: datetime.combine(dia, time(h, m))  # noqa: E731

    # ------------------------------------------------------
    # USUARIOS, VEICULOS E CONTATOS DE CONFIANCA
    # ------------------------------------------------------
    _usuario("admin", "admin@uvv.br", "Administrador CaronaUVV", "Boa Vista",
             is_admin=True, verificado=True)
    kaua = _usuario("202416377", "kaua@uvv.br", "Kauã Araujo", "Itapuã",
                    curso="Ciência da Computação", telefone="27999991111",
                    endereco="Rua Itaúnas, 120", casa_lat=ITAPUA[0], casa_lng=ITAPUA[1],
                    chave_pix="kaua@uvv.br", verificado=True,
                    bio="Estudo à noite e saio de Itapuã todo dia às 18h30. Pontualidade é comigo!",
                    pref_conversa="conversador", pref_musica=True)
    lucas = _usuario("202416378", "lucas@uvv.br", "Lucas Pizzol", "Praia da Costa",
                     curso="Ciência da Computação", telefone="27999992222",
                     endereco="Av. Antônio Gil Veloso, 900",
                     casa_lat=PRAIA_DA_COSTA[0], casa_lng=PRAIA_DA_COSTA[1],
                     chave_pix="27999992222", verificado=True,
                     bio="Curto um rock baixinho no caminho. Aceito mochila e notebook.",
                     pref_conversa="depende", pref_musica=True, pref_animais=True)
    ana = _usuario("202310001", "ana@uvv.br", "Ana Souza", "Itapuã",
                   curso="Direito", telefone="27999993333", endereco="Rua Goiânia, 45",
                   casa_lat=-20.3490, casa_lng=-40.2960, pref_conversa="quieto",
                   bio="Gosto de ir lendo no caminho.")
    pedro = _usuario("202310002", "pedro@uvv.br", "Pedro Lima", "Praia da Costa",
                     curso="Engenharia Civil", telefone="27999994444")
    marina = _usuario("202410003", "marina@uvv.br", "Marina Costa", "Glória",
                      curso="Psicologia", telefone="27999995555", pref_conversa="conversador",
                      verificacao_solicitada_em=datetime.now() - timedelta(hours=5))  # aguardando o admin
    joao = _usuario("202210004", "joao@uvv.br", "João Pereira", "Jardim Camburi",
                    curso="Engenharia de Software", telefone="27999996666", chave_pix="27999996666",
                    verificado=True, pref_conversa="quieto", pref_musica=False,
                    bio="Saio cedo de Camburi para as aulas da manhã.")
    beatriz = _usuario("202410005", "beatriz@uvv.br", "Beatriz Nunes", "Praia de Itaparica",
                       curso="Medicina Veterinária", telefone="27999997777", chave_pix="beatriz@uvv.br",
                       pref_animais=True, bio="Volto da UVV depois da aula das 22h.")

    hb20 = Veiculo(dono=kaua, modelo="HB20", cor="Branco", placa="KAU2B34")
    onix = Veiculo(dono=lucas, modelo="Onix", cor="Prata", placa="LUC4E56")
    gol = Veiculo(dono=joao, modelo="Gol", cor="Vermelho", placa="JOA1B23")
    kwid = Veiculo(dono=beatriz, modelo="Kwid", cor="Azul", placa="BEA9C87")
    mae_da_ana = ContatoConfianca(usuario=ana, nome="Mãe", telefone="27988887777")
    julia = ContatoConfianca(usuario=ana, nome="Júlia", telefone="27988886666")
    db.session.add_all([hb20, onix, gol, kwid, mae_da_ana, julia,
                        ContatoConfianca(usuario=lucas, nome="Mãe", telefone="27988885555")])

    # ------------------------------------------------------
    # CARONA 1 - amanha 18:30, Itapua -> UVV (Ana aceita, Pedro pendente)
    # ------------------------------------------------------
    c_amanha = Carona(
        motorista=kaua, veiculo=hb20, sentido="ida",
        bairro_origem="Itapuã", endereco_origem="Rua Itaúnas, 120",
        origem_lat=ITAPUA[0], origem_lng=ITAPUA[1], destino_lat=UVV[0], destino_lng=UVV[1],
        distancia_km=6.2, duracao_min=18,
        data_hora_saida=as_(amanha, 18, 30), vagas=3, valor_por_passageiro=1.00,
    )
    ana_amanha = Solicitacao(
        carona=c_amanha, passageiro=ana, status="aceita",
        endereco_embarque="Rua Goiânia, 45", embarque_lat=-20.3490, embarque_lng=-40.2960,
        distancia_rota_m=30, desvio_min=1, mensagem="Estou com mochila grande, tudo bem?",
        respondida_em=datetime.now() - timedelta(hours=3),
        expira_em=as_(amanha, 16, 30), pin_embarque="5413",
    )
    pedro_amanha = Solicitacao(
        carona=c_amanha, passageiro=pedro, status="pendente",
        endereco_embarque="Rua Itaúnas, 300", distancia_rota_m=120, desvio_min=2,
        expira_em=as_(amanha, 16, 30),
    )

    # ------------------------------------------------------
    # CARONA 2 - amanha 18:10, Praia da Costa -> UVV (reserva imediata)
    # ------------------------------------------------------
    c_lucas = Carona(
        motorista=lucas, veiculo=onix, sentido="ida",
        bairro_origem="Praia da Costa", endereco_origem="Av. Antônio Gil Veloso, 900",
        origem_lat=PRAIA_DA_COSTA[0], origem_lng=PRAIA_DA_COSTA[1],
        destino_lat=UVV[0], destino_lng=UVV[1], distancia_km=7.5, duracao_min=22,
        data_hora_saida=as_(amanha, 18, 10), vagas=2, valor_por_passageiro=1.50,
        reserva_automatica=True,
    )

    # ------------------------------------------------------
    # CARONA 3 - ontem, concluida (embarque com PIN, Pix, avaliacoes, GPS)
    # ------------------------------------------------------
    c_ontem = Carona(
        motorista=kaua, veiculo=hb20, sentido="ida",
        bairro_origem="Itapuã", endereco_origem="Rua Itaúnas, 120",
        origem_lat=ITAPUA[0], origem_lng=ITAPUA[1], destino_lat=UVV[0], destino_lng=UVV[1],
        distancia_km=6.2, duracao_min=18,
        data_hora_saida=as_(ontem, 18, 30), vagas=3, valor_por_passageiro=1.00,
        status="concluida", iniciada_em=as_(ontem, 18, 31), concluida_em=as_(ontem, 18, 52),
    )
    ana_ontem = Solicitacao(
        carona=c_ontem, passageiro=ana, status="aceita",
        endereco_embarque="Rua Goiânia, 45", distancia_rota_m=30, desvio_min=1,
        respondida_em=as_(ontem, 12, 0), pin_embarque="8271",
        embarcou_em=as_(ontem, 18, 36), metodo_embarque="pin+gps",
    )
    pedro_ontem = Solicitacao(
        carona=c_ontem, passageiro=pedro, status="aceita",
        respondida_em=as_(ontem, 12, 5), faltou=True,  # aparece como "1 falta"
    )
    pix = Pagamento(
        solicitacao=ana_ontem, valor=1.00, metodo="pix", status="pago",
        pix_copia_cola=gerar_pix_copia_cola(kaua.chave_pix, kaua.nome, "Vila Velha", 1.00),
        pago_em=as_(ontem, 18, 55),
    )
    nota_ana = Avaliacao(solicitacao=ana_ontem, avaliador=ana, avaliado=kaua, nota=5,
                         comentario="Pontual e muito educado!", created_at=as_(ontem, 19, 0))
    nota_ana.tags = [AvaliacaoTag(tag="Pontual"), AvaliacaoTag(tag="Dirige bem")]
    nota_kaua = Avaliacao(solicitacao=ana_ontem, avaliador=kaua, avaliado=ana, nota=5, created_at=as_(ontem, 19, 5))
    nota_kaua.tags = [AvaliacaoTag(tag="Pontual"), AvaliacaoTag(tag="Boa conversa")]

    trilha = [
        PosicaoGps(carona=c_ontem, lat=lat, lng=lng, registrada_em=as_(ontem, 18, minuto))
        for minuto, (lat, lng) in zip(
            (31, 36, 42, 48, 52),
            (ITAPUA, (-20.3490, -40.2960), (-20.3530, -40.3000), (-20.3580, -40.3040), UVV),
        )
    ]
    link_familia = LinkCompartilhado(
        carona=c_ontem, usuario=ana, contato=mae_da_ana, token="exemplo-link-familia-ana",
        expira_em=as_(ontem, 18, 52), acessos=3,
    )
    alerta = Alerta(
        carona=c_ontem, usuario=ana, tipo="parada_longa",
        detalhe="6 min parado a 400 m da rota", lat=-20.3530, lng=-40.3000,
        resposta="tudo_bem", respondido_em=as_(ontem, 18, 45),
        status="resolvido", created_at=as_(ontem, 18, 44), resolvido_em=as_(ontem, 18, 45),
    )

    # ------------------------------------------------------
    # CARONA 4 - ontem, cancelada pelo motorista
    # ------------------------------------------------------
    c_cancelada = Carona(
        motorista=lucas, veiculo=onix, sentido="volta",
        # volta: destino = ponto de saida na UVV; endereco_origem = onde deixa no bairro
        bairro_origem="Praia da Costa", endereco_origem="Av. Antônio Gil Veloso, 900",
        destino="UVV - Entrada principal",
        data_hora_saida=as_(ontem, 22, 0), vagas=2, valor_por_passageiro=1.50,
        status="cancelada", cancelada_em=as_(ontem, 17, 0),
    )
    pedro_cancelada = Solicitacao(carona=c_cancelada, passageiro=pedro, status="cancelada")

    db.session.add_all([
        c_amanha, ana_amanha, pedro_amanha, c_lucas,
        c_ontem, ana_ontem, pedro_ontem, pix, nota_ana, nota_kaua, *trilha, link_familia, alerta,
        c_cancelada, pedro_cancelada,
    ])

    # ------------------------------------------------------
    # CARONA 5 - HOJE, daqui a 20 min (demonstracao do ciclo da viagem):
    # Kaua inicia a viagem, digita o PIN da Ana (4821) e conclui.
    # ------------------------------------------------------
    agora = datetime.now().replace(second=0, microsecond=0)
    c_agora = Carona(
        motorista=kaua, veiculo=hb20, sentido="ida",
        bairro_origem="Itapuã", endereco_origem="Rua Itaúnas, 120",
        origem_lat=ITAPUA[0], origem_lng=ITAPUA[1], destino_lat=UVV[0], destino_lng=UVV[1],
        distancia_km=6.2, duracao_min=18, data_hora_saida=agora + timedelta(minutes=20),
        vagas=2, valor_por_passageiro=1.00, observacoes="Saio pontualmente. Cabe mochila no porta-malas.",
    )
    ana_agora = Solicitacao(
        carona=c_agora, passageiro=ana, status="aceita", endereco_embarque="Rua Goiânia, 45",
        respondida_em=agora - timedelta(hours=1), expira_em=agora, pin_embarque="4821",
    )

    # ------------------------------------------------------
    # CARONAS 6 e 7 - amanha, outros bairros (a busca fica mais rica)
    # ------------------------------------------------------
    c_camburi = Carona(
        motorista=joao, veiculo=gol, sentido="ida", bairro_origem="Jardim Camburi",
        endereco_origem="Av. Dante Michelini, 2000", distancia_km=17.0, duracao_min=35,
        data_hora_saida=as_(amanha, 7, 0), vagas=3, valor_por_passageiro=3.00,
        observacoes="Passo pela Terceira Ponte. Sem paradas no caminho.",
    )
    c_volta_bia = Carona(
        motorista=beatriz, veiculo=kwid, sentido="volta", bairro_origem="Praia de Itaparica",
        endereco_origem="Rua Itapemirim, 500", destino="UVV - Entrada principal",
        distancia_km=5.0, duracao_min=14, data_hora_saida=as_(amanha, 22, 10), vagas=2,
        valor_por_passageiro=2.00, reserva_automatica=True,
    )
    db.session.add_all([c_agora, ana_agora, c_camburi, c_volta_bia])

    # ------------------------------------------------------
    # HISTORICO DO KAUA (reputacao de motorista "Veterano" e "Super pontual")
    # - ha 3 dias: Ana, Marina e Lucas (Lucas ainda nao avaliou: aparece em "Avaliar")
    # - ha 5 dias: Ana viajou, Pedro faltou
    # ------------------------------------------------------
    dia3, dia5 = hoje - timedelta(days=3), hoje - timedelta(days=5)
    c_3dias = Carona(
        motorista=kaua, veiculo=hb20, sentido="ida", bairro_origem="Itapuã",
        endereco_origem="Rua Itaúnas, 120", distancia_km=6.2, duracao_min=18,
        data_hora_saida=as_(dia3, 18, 30), vagas=3, valor_por_passageiro=1.00,
        status="concluida", iniciada_em=as_(dia3, 18, 30), concluida_em=as_(dia3, 18, 50),
    )
    c_5dias = Carona(
        motorista=kaua, veiculo=hb20, sentido="ida", bairro_origem="Itapuã",
        endereco_origem="Rua Itaúnas, 120", distancia_km=6.2, duracao_min=18,
        data_hora_saida=as_(dia5, 18, 30), vagas=3, valor_por_passageiro=1.00,
        status="concluida", iniciada_em=as_(dia5, 18, 31), concluida_em=as_(dia5, 18, 49),
    )

    def viagem(carona, passageiro, dia, faltou=False):
        return Solicitacao(carona=carona, passageiro=passageiro, status="aceita",
                           respondida_em=as_(dia, 12, 0), pin_embarque="1111", faltou=faltou,
                           embarcou_em=None if faltou else as_(dia, 18, 35),
                           metodo_embarque=None if faltou else "pin")

    ana_3, marina_3, lucas_3 = viagem(c_3dias, ana, dia3), viagem(c_3dias, marina, dia3), viagem(c_3dias, lucas, dia3)
    ana_5, pedro_5 = viagem(c_5dias, ana, dia5), viagem(c_5dias, pedro, dia5, faltou=True)

    def nota(solicitacao, de, para, valor, dia, tags=(), comentario=None):
        a = Avaliacao(solicitacao=solicitacao, avaliador=de, avaliado=para, nota=valor,
                      comentario=comentario, created_at=as_(dia, 19, 0))
        a.tags = [AvaliacaoTag(tag=t) for t in tags]
        return a

    db.session.add_all([
        c_3dias, c_5dias, ana_3, marina_3, lucas_3, ana_5, pedro_5,
        nota(ana_3, ana, kaua, 5, dia3, ("Pontual", "Carro limpo"), "Sempre no horário!"),
        nota(ana_3, kaua, ana, 5, dia3, ("Pontual", "Educado")),
        nota(marina_3, marina, kaua, 5, dia3, ("Pontual", "Boa conversa"), "Conversa ótima, chegamos rapidinho."),
        nota(marina_3, kaua, marina, 4, dia3, ("Boa conversa",)),
        nota(ana_5, ana, kaua, 5, dia5, ("Pontual", "Dirige bem")),
        nota(ana_5, kaua, ana, 5, dia5, ("Pagou certinho",)),
        Pagamento(solicitacao=marina_3, valor=1.00, metodo="dinheiro", status="pago", pago_em=as_(dia3, 18, 50)),
    ])

    # ------------------------------------------------------
    # NOTIFICACOES (tela 4), DENUNCIA E BUSCAS (painel admin)
    # ------------------------------------------------------
    db.session.add_all([
        Notificacao(usuario=ana, carona=c_amanha, tipo="vaga_confirmada", titulo="Vaga confirmada",
                    texto="Kauã aceitou seu pedido para amanhã às 18:30. Seu PIN é 5413."),
        Notificacao(usuario=kaua, carona=c_amanha, tipo="novo_pedido", titulo="Novo pedido de vaga",
                    texto="Pedro pediu uma vaga na sua carona de amanhã às 18:30."),
        Notificacao(usuario=ana, carona=c_ontem, tipo="motorista_chegando", lida=True,
                    titulo="Kauã está a 3 min do seu ponto",
                    texto="HB20 branco, placa KAU2B34. Seu PIN é 8271."),
        Notificacao(usuario=pedro, carona=c_cancelada, tipo="carona_cancelada", lida=True,
                    titulo="Carona cancelada", texto="Lucas cancelou a carona de ontem às 22:00."),
        Denuncia(denunciante=kaua, denunciado=pedro, carona=c_ontem, motivo="nao_compareceu",
                 descricao="Confirmou a vaga e não apareceu no ponto."),
        Busca(usuario=ana, bairro="Itapuã", sentido="ida", data_desejada=amanha,
              hora_inicio=time(18, 0), hora_fim=time(19, 0), qtd_resultados=1),
        Busca(usuario=pedro, bairro="Praia da Costa", sentido="ida", data_desejada=amanha,
              hora_inicio=time(18, 0), hora_fim=time(19, 0), qtd_resultados=1),
        Busca(usuario=pedro, bairro="Glória", sentido="volta", data_desejada=hoje,
              hora_inicio=time(22, 0), hora_fim=time(23, 0), qtd_resultados=0),
        Busca(bairro="Cobilândia", sentido="ida", data_desejada=hoje, qtd_resultados=0),
        Busca(usuario=marina, bairro="Glória", sentido="ida", data_desejada=amanha, qtd_resultados=0),
        Busca(usuario=marina, bairro="Glória", sentido="volta", data_desejada=amanha, qtd_resultados=0),
        Notificacao(usuario=lucas, carona=c_3dias, tipo="avaliacao_pendente", titulo="Como foi a viagem?",
                    texto="Avalie Kauã e ajude a comunidade a confiar no CaronaUVV."),
    ])
