"""
Gera docs/CaronaUVV_Documentacao.html (e o PDF, com o Microsoft Edge/Chrome instalado).

    python scripts/gerar_documentacao.py            # so o HTML
    python scripts/gerar_documentacao.py --pdf      # HTML + PDF

Os trechos de codigo sao lidos direto dos arquivos-fonte e o diagrama do banco
e montado a partir dos modelos do SQLAlchemy, entao o documento nunca fica
diferente do codigo entregue.
"""
import ast
import html
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
RAIZ = BACKEND.parent
DOCS = RAIZ / "docs"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("LOG_LEVEL", "WARNING")
from caronauvv import create_app  # noqa: E402
from caronauvv.config import TestConfig  # noqa: E402
from caronauvv.ext.db import db  # noqa: E402

# ==========================================================
# TRECHOS DE CODIGO
# ==========================================================


def funcao(caminho: str, nome: str, classe: str | None = None) -> str:
    """Codigo-fonte de uma funcao (ou metodo/classe) do backend."""
    arquivo = RAIZ / caminho
    fonte = arquivo.read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    alvo = arvore
    if classe:
        alvo = next(n for n in ast.walk(arvore) if isinstance(n, ast.ClassDef) and n.name == classe)
        if nome == classe:
            no = alvo
            inicio = (no.decorator_list[0].lineno if no.decorator_list else no.lineno) - 1
            return "\n".join(fonte.splitlines()[inicio:no.end_lineno])
    for no in ast.walk(alvo):
        if isinstance(no, (ast.FunctionDef, ast.ClassDef)) and no.name == nome:
            inicio = (no.decorator_list[0].lineno if no.decorator_list else no.lineno) - 1
            return "\n".join(fonte.splitlines()[inicio:no.end_lineno])
    raise ValueError(f"{nome} nao encontrado em {caminho}")


def linhas(caminho: str, de: str, ate: str, incluir_fim: bool = True) -> str:
    """Trecho entre a primeira linha que contem `de` e a primeira depois dela que contem `ate`."""
    texto = (RAIZ / caminho).read_text(encoding="utf-8").splitlines()
    i = next(n for n, l in enumerate(texto) if de in l)
    j = next(n for n in range(i + 1, len(texto)) if ate in texto[n])
    return "\n".join(texto[i:j + 1 if incluir_fim else j])


def codigo(texto: str, arquivo: str, lang: str = "python") -> str:
    return (f'<div class="codigo"><div class="arquivo">{html.escape(arquivo)}</div>'
            f'<pre><code class="language-{lang}">{html.escape(texto)}</code></pre></div>')


# ==========================================================
# BANCO: diagrama ER (Mermaid) a partir dos modelos
# ==========================================================
def diagrama_dominio(nomes: tuple[str, ...]) -> str:
    """Diagrama de um grupo de tabelas: chaves + colunas principais, so as relacoes entre elas."""
    out = ["erDiagram"]
    for t in db.metadata.sorted_tables:
        if t.name not in nomes:
            continue
        out.append(f"  {t.name} {{")
        for c in t.columns:
            if c.primary_key or c.foreign_keys or c.name in COLUNAS_DESTAQUE:
                tipo = str(c.type).split("(")[0].lower()
                chave = " PK" if c.primary_key else " FK" if c.foreign_keys else ""
                out.append(f"    {tipo} {c.name}{chave}")
        out.append("  }")
    for t in db.metadata.sorted_tables:
        if t.name not in nomes:
            continue
        for c in t.columns:
            for fk in c.foreign_keys:
                if fk.column.table.name in nomes:
                    card = "||--o{" if not c.nullable else "|o--o{"
                    out.append(f'  {fk.column.table.name} {card} {t.name} : "{c.name}"')
    return "\n".join(out)


COLUNAS_DESTAQUE = {
    "nome", "status", "tipo", "token", "expira_em", "motivo", "nota", "tag", "valor", "lat", "lng",
    "bairro", "lida", "chave", "qtd_resultados", "data_hora_saida", "pin_embarque",
}

DOMINIOS = (
    ("Viagem: caronas, pedidos, GPS, avaliações e pagamento",
     ("usuarios", "veiculos", "caronas", "solicitacoes", "posicoes_gps", "avaliacoes", "avaliacao_tags", "pagamentos")),
    ("Segurança: contatos de confiança, link da família, alertas e denúncias",
     ("usuarios", "caronas", "contatos_confianca", "links_compartilhados", "alertas", "denuncias")),
    ("Notificações e administração",
     ("usuarios", "caronas", "notificacoes", "buscas", "configuracoes")),
)


def diagrama_completo() -> str:
    out = ["erDiagram"]
    for t in db.metadata.sorted_tables:
        out.append(f"  {t.name} {{")
        for c in t.columns:
            if c.primary_key or c.foreign_keys:
                tipo = str(c.type).split("(")[0].lower()
                out.append(f"    {tipo} {c.name} {'PK' if c.primary_key else 'FK'}")
        out.append("  }")
    for t in db.metadata.sorted_tables:
        for c in t.columns:
            for fk in c.foreign_keys:
                card = "||--o{" if not c.nullable else "|o--o{"
                out.append(f'  {fk.column.table.name} {card} {t.name} : "{c.name}"')
    return "\n".join(out)


DIAGRAMA_NUCLEO = """erDiagram
  usuarios ||--o{ veiculos : "possui"
  usuarios ||--o{ caronas : "oferece (motorista_id)"
  veiculos |o--o{ caronas : "usado em"
  caronas ||--o{ solicitacoes : "recebe"
  usuarios ||--o{ solicitacoes : "pede (passageiro_id)"
  solicitacoes ||--o{ avaliacoes : "gera"
  solicitacoes ||--o| pagamentos : "rateio"
  usuarios ||--o{ notificacoes : "recebe"
  usuarios {
    int id PK
    string matricula UK
    string email UK
    string nome
    string telefone
    string bairro
    bool email_verificado
    bool verificado
    string pref_conversa
    string senha_hash
  }
  caronas {
    int id PK
    int motorista_id FK
    int veiculo_id FK
    string sentido
    string bairro_origem
    datetime data_hora_saida
    int vagas
    decimal valor_por_passageiro
    string status
  }
  solicitacoes {
    int id PK
    int carona_id FK
    int passageiro_id FK
    string status
    string pin_embarque
    datetime embarcou_em
    bool faltou
  }
  avaliacoes {
    int id PK
    int solicitacao_id FK
    int avaliador_id FK
    int avaliado_id FK
    int nota
  }
  pagamentos {
    int id PK
    int solicitacao_id FK
    decimal valor
    string status
  }
  veiculos {
    int id PK
    int usuario_id FK
    string placa UK
  }
  notificacoes {
    int id PK
    int usuario_id FK
    string tipo
    bool lida
  }"""

DESCRICAO_TABELAS = {
    "usuarios": "Alunos (motorista e passageiro), preferências, verificação de e-mail e selo",
    "veiculos": "Carros do motorista (placa única)",
    "contatos_confianca": "Quem recebe o link da viagem e o aviso de emergência",
    "caronas": "Oferta do motorista: trajeto, horário, vagas, rateio e status",
    "solicitacoes": "Pedido de vaga: status, PIN de embarque, embarque e falta",
    "posicoes_gps": "Trilha GPS da viagem em andamento (link da família)",
    "avaliacoes": "Nota de 1 a 5 entre motorista e passageiro",
    "avaliacao_tags": "Elogios de cada avaliação (Pontual, Dirige bem...)",
    "pagamentos": "Rateio por Pix/dinheiro, com o código Pix copia e cola",
    "notificacoes": "Avisos do sino (pedido novo, vaga confirmada...)",
    "alertas": "Alertas de segurança, inclusive o botão de emergência",
    "links_compartilhados": "Links públicos de acompanhamento da viagem",
    "denuncias": "Denúncias entre usuários e a análise do admin",
    "buscas": "Buscas por bairro (demanda sem oferta no painel)",
    "configuracoes": "Regras ajustáveis: teto do rateio, prazos, segurança",
}


def tabela_banco() -> str:
    linhas_html = []
    for t in db.metadata.sorted_tables:
        fks = sorted({fk.column.table.name for c in t.columns for fk in c.foreign_keys})
        checks = [c.name for c in t.constraints if c.__class__.__name__ == "CheckConstraint"]
        linhas_html.append(
            f"<tr><td><code>{t.name}</code></td><td>{DESCRICAO_TABELAS.get(t.name, '')}</td>"
            f"<td class='c'>{len(t.columns)}</td><td>{', '.join(fks) or '—'}</td><td class='c'>{len(checks)}</td></tr>"
        )
    return ("<table class='compacta'><thead><tr><th>Tabela</th><th>Para que serve</th><th>Colunas</th>"
            "<th>Chaves estrangeiras para</th><th>CHECKs</th></tr></thead><tbody>"
            + "".join(linhas_html) + "</tbody></table>")


def contar_rotas(app) -> int:
    return sum(1 for r in app.url_map.iter_rules() if r.rule.startswith("/api"))


def contar_testes() -> int:
    total = 0
    for arq in (BACKEND / "tests").glob("test_*.py"):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        for no in arvore.body:
            if isinstance(no, ast.FunctionDef) and no.name.startswith("test_"):
                n = 1
                for d in no.decorator_list:
                    if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "parametrize":
                        n = len(d.args[1].elts)
                total += n
    return total


def contar_testes_front() -> int:
    return sum(
        f.read_text(encoding="utf-8").count("\n  it(")
        for f in (RAIZ / "frontend" / "src").rglob("*.test.js")
    )


def contar_telas() -> int:
    return len(list((RAIZ / "frontend" / "src" / "views").glob("*.vue")))


# ==========================================================
# HTML
# ==========================================================
def imagem(nome: str, legenda: str, classe: str = "") -> str:
    return (f'<figure class="{classe}"><img src="img/{nome}" alt="{html.escape(legenda)}">'
            f"<figcaption>{legenda}</figcaption></figure>")


def montar(app) -> str:
    n_rotas, n_tabelas = contar_rotas(app), len(db.metadata.tables)
    n_testes, n_front, n_telas = contar_testes(), contar_testes_front(), contar_telas()
    s = []
    a = s.append

    # ---------------- CAPA ----------------
    a(f"""
<section class="capa">
  <div class="marca">Carona<span>UVV</span></div>
  <h1>Plataforma de caronas entre alunos da Universidade Vila Velha</h1>
  <p class="sub">Documentação do projeto final · Entrega do 2º bimestre (auditoria técnica)</p>
  <div class="numeros">
    <div><b>{n_rotas}</b><span>rotas da API REST</span></div>
    <div><b>{n_tabelas}</b><span>tabelas no banco</span></div>
    <div><b>{n_testes + n_front}</b><span>testes automatizados</span></div>
    <div><b>{n_telas}</b><span>telas em Vue 3</span></div>
  </div>
  <table class="ficha">
    <tr><th>Disciplina</th><td>Desenvolvimento de Sistemas para Web (CC5N)</td></tr>
    <tr><th>Professor</th><td>Wanderson Muniz de Santana</td></tr>
    <tr><th>Curso</th><td>Ciência da Computação · Noturno · UVV</td></tr>
    <tr><th>Integrantes</th><td>Kauã Araujo de Souza (matrícula 202416377)<br>Lucas Pizzol</td></tr>
    <tr><th>Repositório</th><td>github.com/Kauazxz/caronauvv</td></tr>
    <tr><th>Data</th><td>Novembro de 2026</td></tr>
  </table>
</section>""")

    # ---------------- SUMARIO ----------------
    a("""
<section class="quebra">
  <h2>Sumário</h2>
  <ol class="sumario">
    <li>Descrição geral do produto e funcionalidades</li>
    <li>Telas do sistema</li>
    <li>Banco de dados (modelo ER e tabelas)</li>
    <li>Arquitetura adotada</li>
    <li>Detalhamento técnico do código (com trechos)</li>
    <li>Tecnologias utilizadas e justificativa</li>
    <li>Como rodar o projeto (passo a passo)</li>
    <li>Principais desafios e como foram resolvidos</li>
    <li>Onde cada critério técnico da disciplina aparece no projeto</li>
  </ol>
</section>""")

    # ---------------- 1. DESCRICAO ----------------
    a("""
<section class="quebra">
  <h2>1. Descrição geral do produto</h2>
  <p>O <b>CaronaUVV</b> é uma aplicação web que conecta alunos da UVV que fazem trajetos parecidos até o campus,
  para oferecer e pedir caronas de forma organizada e <b>segura</b>.</p>
  <p><b>Problema.</b> Muitos alunos vão sozinhos no próprio carro, enquanto colegas do mesmo bairro dependem de ônibus
  ou de aplicativos pagos. Quando existe carona, ela é combinada em grupos de WhatsApp: as ofertas se perdem, não há
  controle de vagas e, principalmente, <b>não há como saber se a pessoa do outro lado é confiável</b>.</p>
  <p><b>Solução.</b> Um mural de caronas filtrável por bairro, data e horário, em que o passageiro pede a vaga e o
  motorista confirma. Em cima disso, um <b>sistema de confiança</b> inspirado nos aplicativos de carona e transporte
  (BlaBlaCar, Uber, 99): só entra quem tem e-mail da UVV, todo mundo tem reputação pública, o embarque é confirmado
  com PIN, a família pode acompanhar a viagem e existe botão de emergência.</p>
  <p><b>Público-alvo.</b> Motoristas (alunos que vão de carro e têm lugares livres) e passageiros (alunos de bairros
  próximos), principalmente do noturno, que saem em horários fixos.</p>

  <h3>Funcionalidades do MVP</h3>
  <table>
    <thead><tr><th>Funcionalidade</th><th>O que o sistema faz</th></tr></thead>
    <tbody>
      <tr><td>Cadastro e login</td><td>Cadastro com nome, matrícula, e-mail UVV, telefone, bairro e senha; confirmação do e-mail por código; login por e-mail ou matrícula.</td></tr>
      <tr><td>Oferecer carona</td><td>Sentido (ida/volta), bairro, ponto de saída, destino no campus, data, horário, 1 a 6 vagas, rateio (com valor sugerido), carro e observações. Editar e cancelar.</td></tr>
      <tr><td>Buscar caronas</td><td>Só caronas futuras e com vaga, com filtros por bairro, sentido, data e faixa de horário; cada cartão mostra a nota e o nível do motorista.</td></tr>
      <tr><td>Pedir vaga</td><td>O passageiro pede a vaga (ponto de embarque e mensagem opcionais); o motorista aceita ou recusa, ou usa a reserva automática.</td></tr>
      <tr><td>Minhas caronas / Meus pedidos</td><td>Motorista: pedidos recebidos com a reputação de cada passageiro. Passageiro: status, contato do motorista e PIN de embarque.</td></tr>
      <tr><td>Ciclo da viagem</td><td>Iniciar viagem, confirmar o embarque de cada passageiro com o PIN, marcar falta e concluir.</td></tr>
      <tr><td>Telas ao vivo</td><td>Busca, Minhas caronas, Meus pedidos e Notificações se atualizam sozinhas; motorista e passageiro podem ficar lado a lado em duas abas.</td></tr>
    </tbody>
  </table>

  <h3>Sistema de confiança (o que copiamos da engenharia dos grandes apps)</h3>
  <table>
    <thead><tr><th>Recurso</th><th>Como funciona no CaronaUVV</th><th>Inspiração</th></tr></thead>
    <tbody>
      <tr><td>Comunidade fechada</td><td>Cadastro só com e-mail <code>@uvv.br</code> (ou subdomínio); código de 6 números confirma o e-mail. Sem e-mail confirmado não dá para oferecer nem pedir carona.</td><td>BlaBlaCar (e-mail verificado)</td></tr>
      <tr><td>Perfil verificado</td><td>O aluno pede o selo; a administração confere a matrícula e aprova.</td><td>BlaBlaCar (ID verificado)</td></tr>
      <tr><td>Reputação</td><td>Nota média, número de avaliações, nível de experiência (Calouro, Veterano, Embaixador), viagens como motorista e passageiro, faltas, taxa de cancelamento e selos (Super pontual, Muito bem avaliado, Nunca faltou...).</td><td>BlaBlaCar (perfil e níveis)</td></tr>
      <tr><td>Avaliação "às cegas"</td><td>Motorista e passageiro se avaliam (1 a 5 + elogios + comentário) em até 14 dias; a nota só aparece quando os dois avaliam ou depois de 7 dias, para ninguém avaliar por vingança.</td><td>BlaBlaCar (two-way ratings)</td></tr>
      <tr><td>Preferências</td><td>Conversa (prefere silêncio / depende / adora conversar), música, animais e cigarro, no perfil público.</td><td>BlaBlaCar ("Bla, BlaBla, BlaBlaBla")</td></tr>
      <tr><td>PIN de embarque</td><td>O motorista inicia a viagem e digita o PIN de 4 números que o passageiro fala: garante que cada um entrou no carro certo.</td><td>Uber (verificação por PIN)</td></tr>
      <tr><td>Faltas</td><td>Passageiro confirmado que não aparece leva uma falta, visível para o próximo motorista antes de aceitar.</td><td>BlaBlaCar (no-show)</td></tr>
      <tr><td>Link da família</td><td>Página pública (sem login) com motorista, carro, placa, status e última posição GPS no mapa; deixa de funcionar quando a viagem termina.</td><td>Uber (compartilhar status da viagem)</td></tr>
      <tr><td>Botão de emergência</td><td>Gera um alerta para a administração, oferece ligar 190 e avisar os contatos de confiança pelo WhatsApp.</td><td>Uber / 99</td></tr>
      <tr><td>Rateio solidário</td><td>Teto por passageiro (padrão R$ 5,00) e valor sugerido = combustível ÷ ocupantes; pagamento por Pix copia e cola com QR Code.</td><td>BlaBlaCar (preço sugerido)</td></tr>
      <tr><td>Notificações</td><td>Sino com contador: pedido novo, vaga confirmada/recusada, viagem iniciada, embarque, pagamento, avaliação.</td><td>Todos</td></tr>
      <tr><td>Denúncias e moderação</td><td>Só denuncia quem dividiu uma carona; o admin analisa, encerra com resolução e pode suspender a conta.</td><td>Todos</td></tr>
      <tr><td>Painel da administração</td><td>Indicadores (ocupação, CO₂ evitado, faltas, nota média), demanda sem oferta por bairro, verificação de perfis, denúncias, alertas, regras e o banco de dados ao vivo.</td><td>—</td></tr>
    </tbody>
  </table>

  <h3>Regras de negócio implementadas (e testadas)</h3>
  <ul>
    <li>Uma carona nunca tem mais passageiros aceitos do que vagas; quando lota, vira <i>lotada</i> e sai da busca. Se alguém desiste, volta a <i>ativa</i>.</li>
    <li>O motorista não pode pedir vaga na própria carona; o passageiro não pode pedir a mesma carona duas vezes.</li>
    <li>Não é possível criar carona no passado; o rateio não passa do teto configurado.</li>
    <li>Cancelar uma carona cancela os pedidos em aberto e avisa os passageiros.</li>
    <li>Pedido sem resposta expira 2 h antes da saída (ou quando a viagem é iniciada).</li>
    <li>A viagem pode ser iniciada a partir de 30 min antes da saída e precisa de ao menos um passageiro confirmado.</li>
    <li>Embarque só com o PIN certo; o passageiro não pode desistir depois que a viagem começou.</li>
    <li>Telefone e placa só aparecem entre motorista e passageiro depois do aceite.</li>
    <li>Avaliação só depois da carona concluída, uma por pessoa e por viagem, em até 14 dias.</li>
    <li>Login bloqueado por 10 min depois de 5 senhas erradas; o código de e-mail aceita 5 tentativas e vence em 30 min.</li>
    <li>Senhas com hash (Werkzeug/scrypt); o código de verificação é guardado como HMAC-SHA256, nunca em texto.</li>
  </ul>
</section>""")

    # ---------------- 2. TELAS ----------------
    a(f"""
<section class="quebra">
  <h2>2. Telas do sistema</h2>
  <p>O front-end é uma SPA em Vue 3 com Bootstrap 5. No computador o menu fica no topo; no celular vira uma barra
  fixa embaixo, como num aplicativo. São {n_telas} telas.</p>
  {imagem("01_busca.jpg", "Buscar caronas: cada cartão mostra a nota, o nível e o selo de verificado do motorista, além das observações da carona.")}
  {imagem("09_cadastro_validacao.jpg", "Cadastro: cada campo mostra o próprio erro. O domínio do e-mail é validado no navegador e de novo no servidor (Pydantic).")}
</section>
<section class="quebra">
  {imagem("02_perfil_publico.jpg", "Perfil público: nível, selos de confiança, histórico (viagens, faltas, cancelamentos), preferências e elogios mais citados.")}
  {imagem("04_viagem_pin.jpg", "Motorista com a viagem em andamento: link da família, botão de emergência e confirmação do embarque pelo PIN do passageiro.")}
</section>
<section class="quebra">
  {imagem("05_link_familia.jpg", "Link da família (página pública, sem login): motorista, carro, placa e última posição do GPS no mapa.")}
  {imagem("06_pix.jpg", "Passageiro com a vaga confirmada: PIN, Pix copia e cola com QR Code, compartilhar viagem e emergência.")}
</section>
<section class="quebra">
  {imagem("03_avaliacoes.jpg", "Avaliação depois da viagem: estrelas, elogios e comentário. A nota fica escondida até os dois avaliarem.")}
  {imagem("07_admin.jpg", "Painel da administração: indicadores e demanda sem oferta por bairro (buscas que não acharam carona).")}
</section>
<section class="quebra">
  <div class="lado-a-lado">
    {imagem("10_celular.jpg", "No celular: Meus pedidos com PIN, Pix, compartilhar e emergência; menu na parte de baixo.", "celular")}
    <div>
      <h3>Responsividade</h3>
      <p>Todas as telas foram conferidas em 375 px de largura, sem rolagem horizontal (medido no navegador).
      O grid do Bootstrap reorganiza filtros e cartões; botões e campos têm tamanho de toque.</p>
      <h3>Acessibilidade</h3>
      <p>Campos com <code>label</code>, mensagens de erro ligadas ao campo (<code>invalid-feedback</code>),
      estrelas da avaliação como <code>radiogroup</code> com <code>aria-checked</code>, botões de elogio com
      <code>aria-pressed</code> e animações desligadas para quem prefere movimento reduzido.</p>
    </div>
  </div>
</section>""")

    # ---------------- 3. BANCO ----------------
    a(f"""
<section class="quebra">
  <h2>3. Banco de dados</h2>
  <p>O banco tem <b>{n_tabelas} tabelas</b>, definidas como classes Python com Flask-SQLAlchemy 2.0
  (<code>Mapped[...]</code> e <code>mapped_column</code>) e versionadas com Flask-Migrate (Alembic, 2 migrações).</p>
  <p><b>Qual banco e por quê.</b> No desenvolvimento e na apresentação usamos <b>SQLite</b>: é um arquivo
  (<code>backend/instance/caronauvv.db</code>), não precisa instalar servidor e o projeto roda em qualquer máquina.
  Em produção o banco indicado é o <b>PostgreSQL</b> (concorrência real, tipos fortes, transações em DDL); basta
  definir <code>DATABASE_URL</code>, sem mudar código. Não ficamos só na promessa: <b>os {n_testes} testes do back-end
  e as migrações (upgrade, downgrade e upgrade de novo, com dados) foram executados nos dois bancos</b>.</p>

  <h3>Núcleo do modelo (principais colunas)</h3>
  <div class="mermaid nucleo">{html.escape(DIAGRAMA_NUCLEO)}</div>
</section>
<section class="quebra">
  <h3>Modelo completo, por domínio</h3>
  <p class="pequeno">Gerado automaticamente dos modelos do SQLAlchemy (o modelo inteiro aparece ao vivo no painel do
  admin, aba <i>Banco de dados</i>). PK = chave primária, FK = chave estrangeira.</p>
  <h3>{DOMINIOS[0][0]}</h3>
  <div class="mermaid dominio">{html.escape(diagrama_dominio(DOMINIOS[0][1]))}</div>
</section>
<section class="quebra">
  <h3>{DOMINIOS[1][0]}</h3>
  <div class="mermaid dominio">{html.escape(diagrama_dominio(DOMINIOS[1][1]))}</div>
  <h3>{DOMINIOS[2][0]}</h3>
  <div class="mermaid dominio">{html.escape(diagrama_dominio(DOMINIOS[2][1]))}</div>
</section>
<section class="quebra">
  <h3>Tabelas</h3>
  <p class="pequeno">O dicionário de dados completo (cada coluna, tipo e restrição) está em <code>docs/banco_de_dados.md</code>,
  e o esquema SQL do PostgreSQL em <code>docs/schema_postgresql.sql</code> (ambos gerados por <code>invoke docsdb</code>).</p>
  {tabela_banco()}
  <h3>Integridade garantida pelo próprio banco</h3>
  <ul>
    <li><b>Chaves estrangeiras</b> com <code>ON DELETE CASCADE / SET NULL</code> conforme o caso (apagar uma carona apaga pedidos e GPS; apagar um carro deixa a carona antiga sem carro). No SQLite elas são ligadas com <code>PRAGMA foreign_keys=ON</code>.</li>
    <li><b>CHECK constraints</b>: status e sentido só aceitam valores conhecidos, vagas entre 1 e 6, valor ≥ 0, nota entre 1 e 5, ninguém se autoavalia nem se autodenuncia.</li>
    <li><b>UNIQUE</b>: matrícula, e-mail, placa, um pedido por passageiro em cada carona, uma avaliação por pessoa em cada viagem.</li>
    <li><b>Índices</b> nas colunas de busca e <b>naming convention</b> fixa (<code>pk_ fk_ ck_ uq_ ix_</code>), que o Alembic usa para alterar constraints.</li>
  </ul>
</section>""")

    # ---------------- 4. ARQUITETURA ----------------
    a("""
<section class="quebra">
  <h2>4. Arquitetura adotada</h2>
  <p>Duas aplicações que conversam por JSON, no mesmo modelo do projeto TaskFlow visto em aula: uma <b>API REST
  em Flask</b> e uma <b>SPA em Vue 3</b>. No back-end, cada domínio é um pacote com quatro camadas:</p>
  <pre class="diagrama">Navegador (Vue 3 + Bootstrap)
   │  axios ── Authorization: Bearer &lt;token&gt;
   ▼
/api/*  (o Vite repassa para localhost:5000 no desenvolvimento)
   │
Flask ── create_app()   (Application Factory)
   ├─ Blueprints por domínio:
   │     auth · caronas · avaliacoes · notificacoes · seguranca · admin
   │
   │     routes.py   ── recebe a requisição, chama o schema e o service, devolve JSON
   │        │
   │     schemas.py  ── valida o formulário (Pydantic): tipos, tamanhos, regras de campo
   │        │
   │     services.py ── regras de negócio (vagas, PIN, reputação, permissões...)
   │        │
   │     models.py   ── tabelas (SQLAlchemy 2.0)
   │
   ├─ validacao.py   erros do Pydantic → {"error": ..., "campos": {...}} em português
   ├─ errors.py      ApiError / 404 / 405 / 500 → JSON (nunca devolve stack trace)
   ├─ logs.py        uma linha de log por requisição (+ arquivo com rotação)
   ├─ email.py       SMTP ou log em desenvolvimento
   └─ ext/db         Flask-SQLAlchemy + Flask-Migrate → SQLite (dev) / PostgreSQL (prod)</pre>
  <table>
    <thead><tr><th>Pasta / arquivo</th><th>Responsabilidade</th></tr></thead>
    <tbody>
      <tr><td><code>caronauvv/__init__.py</code></td><td>Application Factory: configuração, log, banco, CORS, registro dos 6 módulos e dos erros</td></tr>
      <tr><td><code>config.py</code> + <code>.env</code></td><td>Tudo por variável de ambiente: chave secreta, banco, CORS, log, e-mail, domínios aceitos, proteção do login</td></tr>
      <tr><td><code>auth/</code></td><td>Cadastro, verificação de e-mail, login por token, perfil, perfil público, veículos e contatos de confiança; decorators <code>@login_required</code> e <code>@admin_required</code></td></tr>
      <tr><td><code>caronas/</code></td><td>Caronas e pedidos: busca, criar, editar, cancelar, iniciar, embarque com PIN, falta, GPS, concluir, valor sugerido</td></tr>
      <tr><td><code>avaliacoes/</code></td><td>Avaliações às cegas, reputação, Pix copia e cola e pagamento</td></tr>
      <tr><td><code>notificacoes/</code></td><td>Criação (dentro da mesma transação da ação), listagem, contagem e leitura</td></tr>
      <tr><td><code>seguranca/</code></td><td>Link da família, botão de emergência e denúncias</td></tr>
      <tr><td><code>admin/</code></td><td>Indicadores, moderação, configurações e estrutura do banco</td></tr>
      <tr><td><code>migrations/</code>, <code>tests/</code></td><td>Migrações do Alembic e testes com pytest (SQLite em memória ou PostgreSQL)</td></tr>
      <tr><td><code>frontend/src/</code></td><td>views, components, router (rotas protegidas e de admin), services/api.js, stores (sessão por aba), composables (ao vivo), utils (+ testes Vitest)</td></tr>
    </tbody>
  </table>
  <h3>Exemplo do caminho de uma requisição: "Confirmar embarque"</h3>
  <ol>
    <li>O motorista digita o PIN; o Vue valida o formato (<code>regras.pin</code>) e chama <code>POST /api/solicitacoes/7/embarque</code>.</li>
    <li><code>@login_required</code> lê o token e coloca o usuário em <code>g.usuario</code>.</li>
    <li>A rota valida o corpo com <code>PinSchema</code> (4 números); <code>confirmar_embarque()</code> confere o motorista, a viagem em andamento e o PIN (<code>secrets.compare_digest</code>), grava o embarque e a notificação <b>na mesma transação</b>.</li>
    <li>Regra quebrada vira <code>ApiError</code> → <code>{"error": "PIN incorreto..."}</code>, mostrado embaixo do campo.</li>
  </ol>
</section>""")

    # ---------------- 5. CODIGO ----------------
    a(f"""
<section class="quebra">
  <h2>5. Detalhamento técnico do código</h2>
  <h3>5.1 Application Factory e Blueprints</h3>
  <p>A aplicação é criada por <code>create_app()</code>, que recebe a classe de configuração (a de testes troca o banco
  por SQLite em memória). Cada módulo registra os próprios Blueprints.</p>
  {codigo(funcao("backend/caronauvv/__init__.py", "create_app"), "backend/caronauvv/__init__.py")}
</section>
<section>
  <h3>5.2 Validação dos formulários no servidor (Pydantic)</h3>
  <p>Cada formulário tem um <i>schema</i>. Ele limpa os espaços, converte tipos e aplica as regras de cada campo.
  O cadastro só aceita e-mail institucional:</p>
  {codigo(funcao("backend/caronauvv/auth/schemas.py", "CadastroSchema", classe="CadastroSchema"), "backend/caronauvv/auth/schemas.py")}
  <p>A rota chama <code>validar(Schema, json)</code>. Se algo estiver errado, a resposta traz a mensagem geral e o erro de
  cada campo, em português — o Vue usa esse dicionário para pintar o campo certo:</p>
  {codigo(funcao("backend/caronauvv/validacao.py", "validar"), "backend/caronauvv/validacao.py")}
  {codigo(linhas("backend/caronauvv/auth/routes.py", '@bp.post("/cadastro")', "return _com_codigo_dev"), "backend/caronauvv/auth/routes.py")}
</section>
<section>
  <h3>5.3 Modelo com SQLAlchemy 2.0</h3>
  <p>Modelos tipados, com as regras de integridade declaradas no próprio modelo:</p>
  {codigo(linhas("backend/caronauvv/caronas/models.py", "class Solicitacao(db.Model):", "faltou: Mapped"), "backend/caronauvv/caronas/models.py")}
  <p>A privacidade fica no modelo: o telefone e a placa só entram no JSON para quem participa da viagem.</p>
  {codigo(funcao("backend/caronauvv/caronas/models.py", "pode_ver_contato", classe="Carona"), "backend/caronauvv/caronas/models.py")}
</section>
<section>
  <h3>5.4 Regras de negócio nos services</h3>
  <p><b>Ciclo da viagem (inspirado no Uber).</b> Iniciar exige a janela de 30 minutos e ao menos um passageiro;
  os pedidos pendentes expiram e os passageiros são avisados:</p>
  {codigo(funcao("backend/caronauvv/caronas/services.py", "iniciar_carona"), "backend/caronauvv/caronas/services.py")}
  {codigo(funcao("backend/caronauvv/caronas/services.py", "confirmar_embarque"), "backend/caronauvv/caronas/services.py")}
</section>
<section>
  <p><b>Avaliação às cegas (inspirada no BlaBlaCar).</b> A nota só é revelada quando o outro lado também avaliou ou
  depois do prazo configurado:</p>
  {codigo(funcao("backend/caronauvv/avaliacoes/services.py", "avaliacao_revelada"), "backend/caronauvv/avaliacoes/services.py")}
  <p><b>Rateio solidário.</b> O valor sugerido divide o combustível entre todos e nunca passa do teto:</p>
  {codigo(funcao("backend/caronauvv/caronas/services.py", "valor_sugerido"), "backend/caronauvv/caronas/services.py")}
</section>
<section>
  <h3>5.5 Segurança</h3>
  <ul>
    <li><b>Autenticação por token</b> assinado com a <code>SECRET_KEY</code> (itsdangerous), com validade; conta suspensa invalida o token na hora.</li>
    <li><b>Força bruta</b>: 5 senhas erradas em 10 minutos bloqueiam o login (HTTP 429).</li>
    <li><b>Código de e-mail</b> guardado como HMAC-SHA256, com validade de 30 min e 5 tentativas.</li>
    <li><b>PIN</b> comparado com <code>secrets.compare_digest</code> (tempo constante).</li>
    <li><b>Permissões</b> em cada service (só o motorista inicia, só participante compartilha, só quem dividiu carona denuncia) e <code>@admin_required</code> no painel.</li>
    <li><b>Dados mínimos</b>: perfil público sem telefone/e-mail; link da família expira no fim da viagem.</li>
  </ul>
  {codigo(funcao("backend/caronauvv/auth/services.py", "verificar_email"), "backend/caronauvv/auth/services.py")}
  {codigo(funcao("backend/caronauvv/auth/decorators.py", "admin_required"), "backend/caronauvv/auth/decorators.py")}
</section>
<section>
  <h3>5.6 Tratamento de erros, logging e variáveis de ambiente</h3>
  <p>Toda resposta de erro tem o mesmo formato. Erros de regra de negócio viram <code>ApiError</code>; erros
  inesperados vão para o log com traceback, e o cliente recebe só uma mensagem genérica.</p>
  {codigo(funcao("backend/caronauvv/errors.py", "init_app"), "backend/caronauvv/errors.py")}
  <p>Cada requisição gera uma linha de log com método, rota, status e tempo; com <code>LOG_FILE</code> o log também vai
  para arquivo com rotação (1 MB × 5). Configuração 100% por <code>.env</code> (modelo em <code>.env.example</code>):</p>
  {codigo(linhas("backend/caronauvv/config.py", "def _url_banco", "return url"), "backend/caronauvv/config.py")}
</section>
<section>
  <h3>5.7 Testes automatizados</h3>
  <p><b>{n_testes} testes no back-end</b> (pytest + pytest-flask), com <b>95% de cobertura</b> de código, cobrindo rotas,
  regras de negócio, validação, permissões, banco (FK, CHECK, seed) e Pix. Cada teste roda num banco novo, criado
  pelas fixtures. Os mesmos testes rodam no PostgreSQL definindo <code>TEST_DATABASE_URL</code>.
  No front-end, <b>{n_front} testes com Vitest</b> cobrem as regras de validação e a formatação.</p>
  {codigo(funcao("backend/tests/conftest.py", "viagem"), "backend/tests/conftest.py")}
  {codigo(funcao("backend/tests/test_avaliacoes_pagamentos.py", "test_nota_fica_escondida_ate_os_dois_avaliarem"), "backend/tests/test_avaliacoes_pagamentos.py")}
  <table>
    <thead><tr><th>Arquivo</th><th>O que testa</th></tr></thead>
    <tbody>
      <tr><td><code>test_auth.py</code>, <code>test_validacao_cadastro.py</code></td><td>Cadastro, e-mail institucional, código de verificação, força bruta, perfil e preferências</td></tr>
      <tr><td><code>test_caronas.py</code>, <code>test_solicitacoes.py</code></td><td>Criar, buscar, editar, cancelar; pedir, aceitar, recusar, lotação, expiração</td></tr>
      <tr><td><code>test_ciclo_viagem.py</code>, <code>test_conclusao_e_erros.py</code></td><td>Iniciar, PIN, falta, GPS, concluir, teto e valor sugerido, erros em JSON</td></tr>
      <tr><td><code>test_avaliacoes_pagamentos.py</code></td><td>Avaliação às cegas, reputação, perfil público, Pix e pagamento</td></tr>
      <tr><td><code>test_seguranca_notificacoes.py</code></td><td>Notificações, contatos, link da família, emergência, denúncias</td></tr>
      <tr><td><code>test_admin.py</code>, <code>test_banco.py</code>, <code>test_models.py</code>, <code>test_veiculos.py</code></td><td>Painel, moderação, configurações, integridade do banco e seed</td></tr>
      <tr><td><code>frontend/src/utils/*.test.js</code></td><td>Validação dos formulários e formatação (Vitest)</td></tr>
    </tbody>
  </table>
</section>
<section>
  <h3>5.8 Front-end em Vue 3</h3>
  <p>Um único cliente HTTP coloca o token em toda requisição, volta para o login quando a sessão expira e repassa
  os erros de cada campo vindos do servidor:</p>
  {codigo(linhas("frontend/src/services/api.js", "api.interceptors.response.use(", "export default api", incluir_fim=False), "frontend/src/services/api.js", "javascript")}
  <p>O composable <code>useAoVivo</code> atualiza as telas sozinho (sem sobrepor requisições e pausando com a aba
  escondida); é ele que faz o pedido aparecer na tela do motorista e o sino de notificações contar:</p>
  {codigo(linhas("frontend/src/composables/useAoVivo.js", "export function useAoVivo", "return { atualizadoEm"), "frontend/src/composables/useAoVivo.js", "javascript")}
</section>""")

    # ---------------- 6. TECNOLOGIAS ----------------
    a("""
<section class="quebra">
  <h2>6. Tecnologias utilizadas</h2>
  <table>
    <thead><tr><th>Tecnologia</th><th>Uso no projeto e justificativa</th></tr></thead>
    <tbody>
      <tr><td>Python 3.10+ e Flask 3</td><td>API REST. Stack da disciplina: Application Factory, Blueprints e pytest, como no TaskFlow.</td></tr>
      <tr><td>Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0</td><td>ORM com modelos tipados (<code>Mapped[...]</code>), relacionamentos e constraints.</td></tr>
      <tr><td>Flask-Migrate (Alembic)</td><td>Versionamento do esquema (<code>flask db upgrade/downgrade</code>), em SQLite e PostgreSQL.</td></tr>
      <tr><td>Pydantic 2</td><td>Validação dos formulários no servidor com schemas declarativos (equivalente ao WTForms/Flask-WTF para uma API JSON) e mensagens por campo.</td></tr>
      <tr><td>Flask-CORS e python-dotenv</td><td>Liberar o front-end para chamar a API; configuração por <code>.env</code>.</td></tr>
      <tr><td>itsdangerous, Werkzeug, hmac/secrets</td><td>Token de login assinado, hash de senha (scrypt), HMAC do código de verificação e PIN aleatório seguro.</td></tr>
      <tr><td>SQLite / PostgreSQL (psycopg 3)</td><td>SQLite no desenvolvimento e na apresentação (um arquivo, nada para instalar); PostgreSQL em produção, só trocando a <code>DATABASE_URL</code>. Testado nos dois.</td></tr>
      <tr><td>pytest, pytest-flask, pytest-cov</td><td>Testes das rotas e regras de negócio, com cobertura medida.</td></tr>
      <tr><td>invoke e pyproject.toml</td><td>Empacotamento e tarefas (<code>invoke test</code>, <code>invoke resetdb</code>, <code>invoke docsdb</code>).</td></tr>
      <tr><td>Vue 3, Vite, vue-router, axios</td><td>SPA que consome a API, no padrão do front-end do TaskFlow.</td></tr>
      <tr><td>Bootstrap 5 e Bootstrap Icons</td><td>Framework CSS: grid responsivo, formulários com estado de erro, componentes e ícones.</td></tr>
      <tr><td>Vitest</td><td>Testes do front-end (validação e formatação).</td></tr>
      <tr><td>qrcode, Mermaid</td><td>QR Code do Pix gerado no navegador; diagrama ER desenhado ao vivo no painel. Ambos carregados só na tela que usa.</td></tr>
      <tr><td>OpenStreetMap</td><td>Mapa do link da família, sem chave de API.</td></tr>
      <tr><td>Git e GitHub</td><td>Versionamento, com commits por etapa.</td></tr>
    </tbody>
  </table>
  <p class="pequeno">O documento do MVP previa templates Jinja2 e Flask-Login. Seguimos o padrão mostrado em aula
  (API Flask + Vue 3); por isso a autenticação é por token no cabeçalho e a validação é feita com schemas Pydantic
  sobre o JSON, em vez de formulários renderizados pelo servidor.</p>
</section>""")

    # ---------------- 7. COMO RODAR ----------------
    a("""
<section class="quebra">
  <h2>7. Como rodar o projeto</h2>
  <p><b>Pré-requisitos:</b> Python 3.10 ou mais novo e Node.js 18 ou mais novo. No Windows, extraia o projeto num
  caminho curto (ex.: <code>C:\\caronauvv</code>), porque caminhos longos passam do limite de 260 caracteres e o
  <code>pip</code> falha. São dois terminais.</p>
  <h3>Terminal 1 – API Flask</h3>
  <pre class="terminal">cd backend
python -m venv .venv
.venv\\Scripts\\activate            (Linux/Mac: source .venv/bin/activate)
pip install -e .[dev,test]
copy .env.example .env             (Linux/Mac: cp .env.example .env)
flask --app app.py db upgrade      # cria o banco instance/caronauvv.db
flask --app app.py seed-db         # dados de exemplo (senha de todos: 123456)
flask --app app.py run             # http://localhost:5000/api/health
pytest                             # testes do back-end</pre>
  <h3>Terminal 2 – Front-end Vue</h3>
  <pre class="terminal">cd frontend
npm install
npm run dev                        # abre em http://localhost:5173
npm test                           # testes do front-end (Vitest)</pre>
  <p><b>PostgreSQL (opcional):</b> <code>pip install -e .[postgres]</code>, defina
  <code>DATABASE_URL=postgresql://usuario:senha@localhost:5432/caronauvv</code> no <code>.env</code> e rode
  <code>db upgrade</code> e <code>seed-db</code>.</p>
  <h3>Usuários de exemplo (senha 123456)</h3>
  <table>
    <thead><tr><th>Login</th><th>Para que usar</th></tr></thead>
    <tbody>
      <tr><td><code>kaua@uvv.br</code></td><td>Motorista Veterano, nota 5,0. Tem carona <b>hoje, cerca de 20 min depois do seed</b>, com a Ana confirmada (PIN <b>4821</b>)</td></tr>
      <tr><td><code>lucas@uvv.br</code></td><td>Passageiro com uma avaliação pendente</td></tr>
      <tr><td><code>ana@uvv.br</code> / <code>pedro@uvv.br</code></td><td>Passageira com contatos de confiança / passageiro com 2 faltas</td></tr>
      <tr><td><code>marina@uvv.br</code></td><td>Pediu o selo de verificado (aprovar no painel)</td></tr>
      <tr><td><code>admin@uvv.br</code></td><td>Painel da administração</td></tr>
    </tbody>
  </table>
  <h3>Roteiro de demonstração</h3>
  <ol>
    <li><code>invoke resetdb</code> logo antes de apresentar (recria o banco com o seed).</li>
    <li><b>Cadastro:</b> tentar um e-mail <code>@gmail.com</code> (bloqueado), depois um <code>@uvv.br</code> e confirmar o código.</li>
    <li><b>Aba 1, Kauã:</b> Minhas caronas → carona de hoje → Iniciar viagem → PIN errado e depois 4821 → Compartilhar viagem (abrir o link numa janela anônima) → Concluir → Avaliações.</li>
    <li><b>Aba 2, Lucas:</b> buscar "Itapuã", ver a nota do Kauã e abrir o perfil dele → Pedir vaga. Na aba 1 o pedido chega sozinho; aceitar. Em Meus pedidos: PIN, Pix com QR Code e Emergência.</li>
    <li><b>Admin:</b> indicadores, aprovar o selo da Marina, ver a emergência em Alertas e mostrar o diagrama na aba Banco de dados.</li>
  </ol>
</section>""")

    # ---------------- 8. DESAFIOS ----------------
    a("""
<section class="quebra">
  <h2>8. Principais desafios e como foram resolvidos</h2>
  <p><b>Confiança entre desconhecidos.</b> Num grupo de WhatsApp, não dá para saber quem é a pessoa. Estudamos como
  BlaBlaCar e Uber resolvem isso e adaptamos para a faculdade: comunidade fechada por e-mail institucional,
  reputação pública, avaliação mútua às cegas, PIN de embarque, link da família e botão de emergência.</p>
  <p><b>Controle de vagas sempre correto.</b> Um contador de vagas no banco poderia sair de sincronia. Calculamos
  <code>vagas_restantes</code> a partir das solicitações aceitas e recalculamos o status (ativa/lotada) num único
  ponto, <code>atualizar_lotacao()</code>, chamado em todo aceite e cancelamento.</p>
  <p><b>Avaliação justa.</b> Se a nota aparece na hora, quem avalia por último pode retaliar. A nota fica escondida até
  os dois avaliarem ou até 7 dias, e só quem viajou (não faltou) pode avaliar, uma vez, em até 14 dias.</p>
  <p><b>Validação nos dois lados sem duplicar mensagens.</b> O navegador valida para responder rápido, mas a regra
  vale no servidor. Os schemas Pydantic devolvem o erro de cada campo em português, e o Vue junta esses erros com os
  dele (<code>errosDoServidor</code>), então até uma regra que só o servidor conhece aparece no campo certo.</p>
  <p><b>Migrações com dados no SQLite e no PostgreSQL.</b> O SQLite não tem <code>ALTER TABLE</code> completo, então o
  Alembic recria a tabela (modo <i>batch</i>). Com as chaves estrangeiras ligadas, recriar <code>usuarios</code>
  falhava quando já havia dados. Desligamos a checagem só durante a migração e conferimos tudo no final com
  <code>PRAGMA foreign_key_check</code>. No PostgreSQL, o <i>downgrade</i> falhava porque existiam embarques com o novo
  método "pin": a migração passou a converter esses dados antes de restaurar a constraint antiga. Testamos
  upgrade → downgrade → upgrade com o banco populado nos dois bancos.</p>
  <p><b>Notificação consistente.</b> Se a notificação fosse gravada separada da ação, uma falha poderia avisar algo que
  não aconteceu. <code>notificar()</code> não faz commit: entra na mesma transação da ação que a gerou.</p>
  <p><b>Desempenho da reputação.</b> A busca pode mostrar o mesmo motorista várias vezes. A reputação é calculada uma
  vez por requisição e guardada no <code>environ</code> da requisição (um primeiro cache em <code>g</code> vazava entre
  requisições nos testes — os próprios testes pegaram o problema).</p>
  <p><b>Suíte de testes rápida.</b> Com a verificação de e-mail, cada aluno de teste passou a gerar mais hashes e a
  suíte subiu para 148 s. O código de verificação passou a usar HMAC (adequado para um código curto com validade e
  limite de tentativas) e os testes usam um hash de senha mais leve: a suíte roda em cerca de 12 s.</p>
  <p><b>Login numa API sem páginas.</b> O Flask-Login depende de sessão e templates; como o front é uma SPA, usamos
  token assinado no cabeçalho <code>Authorization</code>, validado por <code>@login_required</code>.</p>
  <p><b>Pedidos que ninguém respondeu.</b> Sem agendador, um pedido pendente ficaria pendente para sempre. Cada pedido
  tem prazo (<code>expira_em</code>) e os vencidos expiram quando as listas são consultadas, quando a viagem é iniciada
  ou quando a carona é concluída.</p>
  <p><b>Duas pessoas ao mesmo tempo.</b> Em vez de WebSockets (outro servidor), o composable <code>useAoVivo</code>
  consulta a API a cada poucos segundos e destaca o que mudou; o login fica no <code>sessionStorage</code>, então
  motorista e passageiro podem ficar lado a lado no mesmo navegador.</p>
  <p><b>Uso no celular.</b> A maioria dos alunos usa o celular: grid do Bootstrap, barra de navegação embaixo e cada
  tela conferida em 375 px de largura, sem rolagem horizontal.</p>
</section>""")

    # ---------------- 9. CRITERIOS ----------------
    a(f"""
<section class="quebra">
  <h2>9. Onde cada critério técnico aparece no projeto</h2>
  <table>
    <thead><tr><th>Critério</th><th>Onde conferir</th></tr></thead>
    <tbody>
      <tr><td>1. Arquitetura modular e fábrica de aplicação</td><td><code>create_app()</code> em <code>caronauvv/__init__.py</code> recebendo a classe de configuração; extensões desacopladas em <code>extensions.py</code> e <code>ext/db</code> (seção 5.1).</td></tr>
      <tr><td>2. Módulos / Blueprints / rotas</td><td>6 pacotes de domínio (auth, caronas, avaliacoes, notificacoes, seguranca, admin), cada um com <code>routes.py</code> (Blueprint), <code>schemas.py</code>, <code>services.py</code> e <code>models.py</code>; {n_rotas} rotas (seção 4).</td></tr>
      <tr><td>3. Formulários e validação</td><td>Schemas Pydantic no servidor com erro por campo (<code>validacao.py</code>, <code>*/schemas.py</code>) + validação no Vue (<code>utils/validacao.js</code>) (seção 5.2).</td></tr>
      <tr><td>4. Interface / front-end</td><td>Vue 3 + Bootstrap 5, {n_telas} telas, responsivo (barra inferior no celular), componentes reutilizáveis (seção 2).</td></tr>
      <tr><td>5. Testes automatizados</td><td>{n_testes} testes pytest (rotas e regras, 95% de cobertura, também no PostgreSQL) + {n_front} testes Vitest (seção 5.7).</td></tr>
      <tr><td>6. Persistência e ORM</td><td>SQLAlchemy 2.0, {n_tabelas} tabelas com FK, CHECK, UNIQUE e índices; 2 migrações Alembic; SQLite e PostgreSQL (seção 3).</td></tr>
      <tr><td>7. Qualidade de código</td><td>Pastas por responsabilidade, <code>.env</code>, logging com rotação, erros centralizados em JSON, código e nomes em português legíveis, histórico de commits no Git.</td></tr>
    </tbody>
  </table>
</section>""")
    return "\n".join(s)


CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; color: #1d2433; font-size: 10.5pt; line-height: 1.45; margin: 0; }
h2 { color: #0b2a5b; font-size: 18pt; margin: 0 0 8px; border-bottom: 3px solid #ffc72c; padding-bottom: 4px; }
h3 { color: #163f82; font-size: 12.5pt; margin: 14px 0 6px; }
p { margin: 6px 0; }
code { font-family: Consolas, 'Cascadia Mono', monospace; font-size: 9pt; background: #eef2f8; padding: 0 3px; border-radius: 3px; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9.2pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #d5dce8; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #0b2a5b; color: #fff; }
tbody tr:nth-child(even) td { background: #f6f8fb; }
td.c { text-align: center; }
table.compacta { font-size: 8.4pt; } table.compacta td, table.compacta th { padding: 2px 5px; }
.quebra { page-break-before: always; }
.capa { text-align: center; padding-top: 40mm; }
.capa .marca { font-size: 42pt; font-weight: 800; color: #0b2a5b; }
.capa .marca span { color: #e0a800; }
.capa h1 { font-size: 17pt; color: #163f82; margin: 6px 0; }
.capa .sub { color: #5b6880; }
.numeros { display: flex; justify-content: center; gap: 14px; margin: 26px 0; }
.numeros div { border: 2px solid #163f82; border-radius: 10px; padding: 10px 14px; min-width: 110px; }
.numeros b { display: block; font-size: 24pt; color: #0b2a5b; }
.numeros span { font-size: 9pt; color: #5b6880; }
.ficha { width: 75%; margin: 10px auto; font-size: 10.5pt; }
.ficha th { width: 30%; }
.sumario li { margin: 6px 0; font-size: 12pt; }
figure { margin: 8px 0 14px; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; max-height: 118mm; border: 1px solid #d5dce8; border-radius: 6px; }
figcaption { font-size: 9pt; color: #5b6880; margin-top: 4px; }
.lado-a-lado { display: flex; gap: 16px; align-items: flex-start; }
.lado-a-lado figure.celular img { max-height: 190mm; }
.lado-a-lado figure.celular { width: 48%; flex-shrink: 0; }
.codigo { margin: 8px 0; border: 1px solid #d5dce8; border-radius: 6px; }
.codigo .arquivo { background: #0b2a5b; color: #fff; font-size: 8.5pt; padding: 3px 8px; font-family: Consolas, monospace; break-after: avoid; }
h3, h2 { break-after: avoid; }
.codigo pre { margin: 0; padding: 8px; background: #f6f8fb; font-size: 8pt; line-height: 1.35; white-space: pre-wrap; }
pre.diagrama { font-size: 7.4pt !important; line-height: 1.2 !important; }
pre.diagrama, pre.terminal { background: #0f1a2e; color: #e6edf7; padding: 8px 10px; border-radius: 6px; font-size: 8pt; line-height: 1.3; white-space: pre-wrap; page-break-inside: avoid; }
.mermaid { text-align: center; margin: 8px 0; }
.mermaid svg { max-width: 100%; height: auto; }
.mermaid.nucleo svg { max-height: 182mm; width: auto !important; max-width: 100%; }
@page paisagem { size: A4 landscape; margin: 10mm; }
.paisagem { page: paisagem; }
.mermaid.completo svg { max-height: 172mm; width: auto !important; max-width: 100%; }
.mermaid.dominio svg { max-height: 112mm; width: auto !important; max-width: 100%; }
section.quebra:has(.dominio) .mermaid.dominio:only-of-type svg { max-height: 215mm; }
.pequeno { font-size: 9pt; color: #5b6880; }
ul { margin: 6px 0; padding-left: 20px; } li { margin: 3px 0; }
"""


def gerar(pdf: bool) -> Path:
    app = create_app(TestConfig)
    with app.app_context():
        corpo = montar(app)
    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>CaronaUVV - Documentação</title>
<style>{CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>
</head><body>
{corpo}
<script>
  mermaid.initialize({{ startOnLoad: false, theme: 'neutral', er: {{ useMaxWidth: true }} }});
  mermaid.run({{ querySelector: '.mermaid' }}).then(() => {{ document.body.dataset.pronto = '1'; }});
</script>
</body></html>"""
    saida = DOCS / "CaronaUVV_Documentacao.html"
    saida.write_text(pagina, encoding="utf-8")
    print(f"HTML: {saida}")
    if pdf:
        navegador = (shutil.which("msedge") or shutil.which("chrome")
                     or next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                                          r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                                          r"C:\Program Files\Google\Chrome\Application\chrome.exe")
                              if Path(p).exists()), None))
        if not navegador:
            raise SystemExit("Edge/Chrome nao encontrado para gerar o PDF.")
        destino = DOCS / "CaronaUVV_Documentacao.pdf"
        subprocess.run([
            navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
            "--virtual-time-budget=20000", f"--print-to-pdf={destino}", saida.as_uri(),
        ], check=True, capture_output=True)
        print(f"PDF: {destino}")
    return saida


if __name__ == "__main__":
    gerar("--pdf" in sys.argv)
