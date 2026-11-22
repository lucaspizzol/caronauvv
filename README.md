# CaronaUVV

Plataforma web de caronas entre alunos da UVV (Universidade Vila Velha). Trabalho da disciplina
**Desenvolvimento de Sistemas para Web (CC5N)** — Ciência da Computação, noturno.

O motorista publica uma carona (bairro de saída, horário, vagas e valor do rateio), os passageiros
pedem vaga e o motorista aceita ou recusa. O telefone de cada um só aparece depois do aceite.

## Tecnologias

- **Back-end:** Python, Flask (API REST em JSON), Flask-SQLAlchemy 2.0, Flask-Migrate, Flask-CORS
- **Banco:** SQLite no desenvolvimento, PostgreSQL em produção (`DATABASE_URL`)
- **Testes:** pytest + pytest-flask
- **Front-end:** Vue 3 + Vite + vue-router + axios, com Bootstrap 5 e Bootstrap Icons (pasta `frontend/`), responsivo para celular

## Estrutura

```
backend/
  app.py                  # ponto de entrada (create_app)
  caronauvv/
    __init__.py           # Application Factory, CORS, blueprints
    config.py             # Config e TestConfig
    ext/db/               # SQLAlchemy, comandos init-db / seed-db / limpar-gps
    auth/                 # usuários, login por token, veículos
    caronas/              # caronas e solicitações de vaga
    avaliacoes/           # avaliações, tags e pagamentos (Pix)
    notificacoes/
    seguranca/            # alertas, link da família, denúncias
    admin/                # buscas e configurações
  migrations/             # Flask-Migrate (Alembic)
  scripts/                # geração da documentação do banco
  tests/                  # 99 testes (pytest + pytest-flask)
  .env.example            # variaveis de ambiente (copiar para .env)
frontend/
  src/
    main.js               # cria o app Vue, Bootstrap e rotas
    router/               # rotas e protecao de login
    services/api.js       # axios: token no cabecalho e mensagens de erro da API
    stores/auth.js        # sessao do usuario (token no sessionStorage, uma por aba)
    composables/          # useAoVivo: atualizacao automatica das telas
    views/                # telas: login, cadastro, busca, oferecer/editar, minhas caronas, meus pedidos, perfil
    components/           # NavBar, CaronaInfo, StatusBadge, AlertaMensagem, BotaoConfirmar
    utils/                # formatacao e validacao dos formularios
docs/
  CaronaUVV_MVP.docx      # documento do MVP
  banco_de_dados.md       # diagrama ER (Mermaid) e dicionário de dados
  banco.dbml              # diagrama para o dbdiagram.io
  schema_postgresql.sql   # esquema para PostgreSQL
```

## Como rodar

São dois terminais: um para a API Flask e outro para o front-end Vue.

**1. API (Flask)**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate
pip install -e .[dev,test]
cp .env.example .env             # Windows: copy .env.example .env

flask --app app.py db upgrade    # cria instance/caronauvv.db
flask --app app.py seed-db       # dados de exemplo (senha de todos: 123456)
flask --app app.py run           # API em http://localhost:5000/api/health
pytest                           # testes
```

Tarefas com invoke: `invoke createdb`, `invoke seed`, `invoke resetdb`, `invoke docsdb`, `invoke test`.

**2. Front-end (Vue 3)** — precisa do Node.js 18 ou mais novo

```bash
cd frontend
npm install
npm run dev                      # abre em http://localhost:5173
```

O Vite repassa as chamadas `/api` para o Flask em `localhost:5000` (proxy em `vite.config.js`).
Para gerar a versão de produção: `npm run build` (sai na pasta `dist/`).

Usuários de exemplo: `admin@uvv.br`, `kaua@uvv.br`, `lucas@uvv.br`, `ana@uvv.br`, `pedro@uvv.br` (senha `123456`).
Também dá para entrar com a matrícula no lugar do e-mail.

### Demonstração com duas telas (motorista e passageiro)

As telas **Buscar caronas**, **Minhas caronas** e **Meus pedidos** se atualizam sozinhas a cada 5 segundos
(indicador "Ao vivo"), e o login é guardado por aba. Assim dá para mostrar os dois lados ao mesmo tempo:

1. `flask --app app.py seed-db` com o banco zerado (`invoke resetdb` apaga e recria).
2. Aba/janela 1: entre com `kaua@uvv.br` e abra **Minhas caronas** (motorista).
3. Aba/janela 2: entre com `lucas@uvv.br`, busque "Itapuã" e clique em **Pedir vaga** na carona do Kauã.
4. Em até 5 s o pedido aparece na tela do motorista, piscando em amarelo. Clique em **Aceitar**.
5. Em **Meus pedidos** do passageiro, o status muda para "Vaga confirmada" e aparecem o telefone e o PIN.

Para usar o celular como segunda tela, deixe o PC e o celular na mesma rede e abra `http://IP-do-PC:5173`.

## API

| Recurso | Rotas |
|---|---|
| Autenticação | `POST /api/auth/cadastro`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET/PUT /api/auth/me` |
| Veículos | `GET/POST /api/veiculos`, `PUT/DELETE /api/veiculos/<id>` |
| Caronas | `GET/POST /api/caronas`, `GET /api/caronas/minhas`, `GET/PUT /api/caronas/<id>`, `POST /api/caronas/<id>/cancelar`, `POST /api/caronas/<id>/concluir` |
| Solicitações | `GET/POST /api/caronas/<id>/solicitacoes`, `GET /api/solicitacoes/minhas`, `POST /api/solicitacoes/<id>/aceitar`, `/recusar`, `/cancelar` |

Rotas protegidas usam o cabeçalho `Authorization: Bearer <token>`. Lista completa: `flask --app app.py routes`.

Todo erro volta em JSON no formato `{"error": "mensagem"}` (regras de negócio, 404, 405 e 500), e cada
requisição é registrada no log com método, rota, status e tempo (nível em `LOG_LEVEL` no `.env`).

## Regras de negócio

- Uma carona não pode ter mais passageiros aceitos do que vagas; quando lota, fica `lotada` e sai da busca.
- O motorista não pode pedir vaga na própria carona, e o passageiro não pode pedir a mesma carona duas vezes.
- Não é possível criar carona com data/hora no passado.
- Cancelar uma carona cancela as solicitações em aberto.
- Pedido sem resposta expira 2 h antes da saída.
- O telefone só aparece entre motorista e passageiro depois que a solicitação é aceita.
- Depois do horário da viagem, o motorista marca a carona como concluída; pedidos sem resposta expiram.
- Senhas guardadas com hash (Werkzeug).

## Banco de dados

15 tabelas, documentadas em [`docs/banco_de_dados.md`](docs/banco_de_dados.md). Para ver o diagrama
visual, cole o conteúdo de [`docs/banco.dbml`](docs/banco.dbml) em [dbdiagram.io](https://dbdiagram.io).
