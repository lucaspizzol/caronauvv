# CaronaUVV

Plataforma web de caronas entre alunos da UVV (Universidade Vila Velha). Trabalho da disciplina
**Desenvolvimento de Sistemas para Web (CC5N)** — Ciência da Computação, noturno.

O motorista publica uma carona (bairro de saída, horário, vagas e valor do rateio), os passageiros
pedem vaga e o motorista aceita ou recusa. O telefone de cada um só aparece depois do aceite.

Por cima do MVP, o CaronaUVV tem um **sistema de confiança** inspirado nos apps de carona e de
transporte (BlaBlaCar, Uber, 99):

| Recurso | Como funciona | Inspiração |
|---|---|---|
| Só alunos da UVV | Cadastro aceita apenas e-mail `@uvv.br` e confirma o e-mail com código de 6 números | BlaBlaCar (e-mail verificado) |
| Perfil verificado | O aluno pede o selo e a administração confere a matrícula | BlaBlaCar (perfil verificado) |
| Foto de perfil | O aluno envia a foto pelo perfil; ela aparece na busca, nos pedidos, nas avaliações, no perfil público e no link da família. O admin pode remover foto inadequada | Uber / BlaBlaCar |
| Verificação em duas etapas | Com um aplicativo autenticador (Google Authenticator, Microsoft Authenticator, Authy), o login pede a senha e um código de 6 números; 8 códigos de reserva de uso único | Uber, bancos, GitHub (2FA) |
| Esqueci minha senha | Código de 6 números enviado ao e-mail da conta; a senha nova desconecta os outros aparelhos | Todos |
| Reputação | Nota média, nível (Calouro → Veterano → Embaixador), viagens, faltas, taxa de cancelamento e selos | BlaBlaCar |
| Avaliação "às cegas" | Motorista e passageiro se avaliam (1 a 5 + elogios); a nota só aparece quando os dois avaliam ou após 7 dias | BlaBlaCar |
| Preferências | Conversa (silêncio / depende / adora conversar), música, animais, fumar | BlaBlaCar ("Bla, BlaBla, BlaBlaBla") |
| PIN de embarque | O motorista inicia a viagem e digita o PIN de 4 números de cada passageiro | Uber (verificação por PIN) |
| Faltas | Passageiro confirmado que não aparece leva uma falta no perfil | BlaBlaCar (no-show) |
| Link da família | Página pública com motorista, carro, placa e última localização GPS; expira no fim da viagem | Uber (compartilhar viagem) |
| Botão de emergência | Avisa a administração, oferece ligar 190 e avisar os contatos de confiança | Uber / 99 |
| Rateio solidário | Teto por passageiro e valor sugerido (combustível ÷ ocupantes); Pix copia e cola com QR Code | BlaBlaCar (preço sugerido) |
| Notificações | Sino com contador: pedido novo, vaga confirmada, viagem iniciada, avaliação etc. | Todos |
| Denúncias e moderação | Só denuncia quem dividiu carona; admin analisa, encerra e pode suspender | Todos |
| Painel admin | KPIs (ocupação, CO₂ evitado, faltas), demanda sem oferta por bairro, regras e **banco de dados ao vivo** | — |

## Tecnologias

- **Back-end:** Python, Flask (API REST em JSON), Flask-SQLAlchemy 2.0, Flask-Migrate, Flask-CORS
- **Validação no servidor:** Pydantic 2 (schemas de cada formulário, erros por campo em português)
- **Banco:** SQLite no desenvolvimento, PostgreSQL em produção (`DATABASE_URL`) — os 255 testes passam nos dois
- **Testes:** pytest + pytest-flask (back-end, 255 testes, 96% de cobertura) e Vitest (front-end, 20 testes)
- **Segurança da conta:** TOTP (RFC 6238) feito com a biblioteca padrão do Python (`hmac`, `hashlib`, `struct`),
  tokens e desafios assinados com itsdangerous, senhas com hash scrypt (Werkzeug)
- **Front-end:** Vue 3 + **TypeScript (modo estrito)** + Vite + vue-router + axios, Bootstrap 5 e Bootstrap Icons,
  responsivo para celular; os tipos das respostas da API ficam em `src/types/api.ts` e o `vue-tsc` confere código e
  templates antes de cada build;
  `qrcode` (QR do Pix) e `mermaid` (diagrama do banco no painel)

## Estrutura

```
backend/
  app.py                  # ponto de entrada (create_app)
  caronauvv/
    __init__.py           # Application Factory, CORS, blueprints
    config.py             # Config e TestConfig (tudo vem do .env)
    validacao.py          # base dos schemas Pydantic e traducao dos erros
    email.py              # envio de e-mail (SMTP) ou log em desenvolvimento
    errors.py, logs.py    # erros em JSON e log de cada requisicao
    ext/db/               # SQLAlchemy, comandos init-db / seed-db / limpar-gps, seed
    auth/                 # usuarios, login, verificacao de e-mail, perfil publico, veiculos, contatos
                          #   foto.py (foto de perfil), totp.py + dois_fatores.py (verificacao em duas etapas)
    caronas/              # caronas, pedidos de vaga, ciclo da viagem (iniciar, PIN, falta, GPS)
    avaliacoes/           # avaliacoes, reputacao e pagamento Pix
    notificacoes/         # notificacoes
    seguranca/            # link da familia, botao de emergencia, denuncias
    admin/                # painel: indicadores, moderacao, configuracoes, estrutura do banco
    (cada modulo: models.py, schemas.py, services.py, routes.py)
  migrations/             # Flask-Migrate (Alembic): 3 versoes
  scripts/                # geracao da documentacao do banco
  tests/                  # 255 testes (pytest + pytest-flask)
frontend/
  src/
    types/api.ts          # formato de cada resposta da API (espelha os to_dict() do back-end)
    router/, services/api.ts, stores/auth.ts, composables/useAoVivo.ts
    views/                # 15 telas (busca, oferecer, minhas caronas, pedidos, avaliacoes,
                          #   notificacoes, perfil, perfil publico, admin, link da familia,
                          #   login em duas etapas, recuperar senha...)
    components/           # NavBar, CaronaInfo, AvatarUsuario, FotoPerfilEditor, DoisFatores,
                          #   ReputacaoResumo, EstrelasNota, PixPagamento, SegurancaViagem,
                          #   StatusBadge, AlertaMensagem, BotaoConfirmar
    utils/                # formatacao, validacao e recorte da foto (+ testes *.test.ts)
docs/                     # documentacao do banco (gerada a partir dos modelos)
```

## Como rodar

Precisa de **Python 3.10+** e **Node.js 18+**. São dois terminais: um para a API Flask e outro para o Vue.

> Dica (Windows): extraia o projeto num caminho curto, como `C:\caronauvv`. Caminhos muito longos
> passam do limite de 260 caracteres do Windows e o `pip install` falha.

**1. API (Flask)**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate
pip install -e .[dev,test]
cp .env.example .env             # Windows: copy .env.example .env

python -m flask --app app.py db upgrade    # cria instance/caronauvv.db
python -m flask --app app.py seed-db       # dados de exemplo (senha de todos: 123456)
python -m flask --app app.py run           # API em http://localhost:5000/api/health
python -m pytest                           # 255 testes
```

Tarefas com invoke: `invoke createdb`, `invoke seed`, `invoke resetdb`, `invoke docsdb`, `invoke test`, `invoke run`, `invoke docs`.

> Usamos `python -m flask` e `python -m pytest` (em vez de só `flask`/`pytest`) porque alguns Windows
> com **Device Guard / Smart App Control** bloqueiam os `.exe` criados dentro do `.venv\Scripts`.
> As tarefas do `invoke` já fazem isso sozinhas.

**2. Front-end (Vue 3)**

```bash
cd frontend
npm install
npm run dev                      # abre em http://localhost:5173
npm test                         # 20 testes do front (Vitest)
npm run type-check               # checagem do TypeScript (vue-tsc)
```

O Vite repassa as chamadas `/api` para o Flask em `localhost:5000` (proxy em `vite.config.ts`).
Para gerar a versão de produção: `npm run build` (confere os tipos e sai na pasta `dist/`).

### PostgreSQL (produção)

```bash
pip install -e .[postgres]       # driver psycopg 3
# no .env: DATABASE_URL=postgresql://usuario:senha@localhost:5432/caronauvv
python -m flask --app app.py db upgrade && python -m flask --app app.py seed-db
# testes no PostgreSQL: TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/caronauvv_test pytest
```

### Versão online (Vercel)

O sistema está publicado em **https://caronauvv.vercel.app**:

- o Vue é gerado no build (`frontend/dist`) e servido como site estático;
- a API Flask roda como função serverless (`api/index.py`, dependências em `requirements.txt`);
- o banco é um **PostgreSQL Neon** (plano grátis), ligado ao projeto pela variável `DATABASE_URL`;
- `APP_TZ=<-03>3` deixa o servidor (que roda em UTC) no horário de Brasília;
- configuração em `vercel.json` e variáveis no painel da Vercel (`SECRET_KEY`, `APP_TZ`, `MOSTRAR_CODIGO_DEV`...).

Publicar de novo: `vercel deploy --prod` na pasta raiz. **Zerar o banco online** com os dados de exemplo
(faça antes de apresentar): `invoke resetvercel` dentro de `backend/`, com a CLI da Vercel logada.

> **Atenção ao publicar uma versão com migração nova** (como a da foto de perfil e do autenticador): o banco
> online precisa ser atualizado junto, senão a API responde erro 500. Rode `invoke resetvercel` logo depois do
> `vercel deploy --prod` (ele aplica as migrações e recria os dados de exemplo). Para manter os dados que já
> estão lá, rode só `flask --app app.py db upgrade` com a `DATABASE_URL` do Neon.

As fotos de perfil ficam no próprio banco (tabela `fotos_perfil`), porque a função serverless não guarda
arquivos em disco.

> A versão online usa as mesmas contas de exemplo (senha `123456`): qualquer pessoa com o link
> consegue entrar. É uma demonstração; para uso real, troque as senhas e configure um servidor de e-mail.
> Com `MOSTRAR_CODIGO_DEV=1`, os códigos de verificação de e-mail e de "esqueci minha senha" aparecem na tela
> em vez de irem só para o e-mail: em produção de verdade, use `MOSTRAR_CODIGO_DEV=0` e configure o SMTP.

## Usuários de exemplo (senha `123456`)

| E-mail | Papel na demonstração |
|---|---|
| `kaua@uvv.br` | Motorista "Veterano", nota 5,0, perfil verificado. Tem uma carona **hoje, ~20 min depois do seed** (Ana confirmada, PIN **4821**) |
| `lucas@uvv.br` | Passageiro; tem uma avaliação pendente do Kauã |
| `ana@uvv.br` | Passageira com contatos de confiança (Mãe, Júlia) |
| `pedro@uvv.br` | Passageiro com 2 faltas (aparece para o motorista antes de aceitar) |
| `marina@uvv.br` | Pediu o selo de verificado (aprovar no painel) |
| `joao@uvv.br` | Outro motorista (Jardim Camburi) |
| `beatriz@uvv.br` | Motorista (Praia de Itaparica) que **já usa a verificação em duas etapas**: o login pede o código. Use um código de reserva de exemplo (`UVVA-2026`, `UVVB-2026`, `UVVC-2026`, `UVVD-2026`; cada um vale uma vez) ou cadastre a chave `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP` num aplicativo autenticador |
| `admin@uvv.br` | Painel da administração (`/admin`) |

Kauã, Lucas, Ana e João já vêm com foto de perfil (avatares desenhados, não são fotos de pessoas reais); os
outros aparecem com as iniciais. Também dá para entrar com a matrícula no lugar do e-mail. Sem servidor de e-mail configurado, o
código de verificação do cadastro aparece na própria tela ("modo de demonstração") e no log da API.

### Roteiro de demonstração (duas abas: motorista e passageiro)

As telas **Buscar**, **Minhas caronas**, **Meus pedidos** e **Notificações** se atualizam sozinhas
(indicador "Ao vivo") e o login é guardado por aba.

1. `invoke resetdb` (apaga e recria o banco com o seed) — faça isso logo antes de apresentar.
2. **Cadastro:** tente `fulano@gmail.com` (bloqueado) e depois `fulano@uvv.br`; confirme o código.
3. **Aba 1 — Kauã:** Minhas caronas → carona de hoje → **Iniciar viagem** → digite o PIN **4821** da Ana
   (teste um PIN errado antes) → **Compartilhar viagem** (abra o link numa janela anônima) → **Concluir**
   → **Avaliações**.
4. **Aba 2 — Lucas:** busque "Itapuã" → veja a nota do Kauã → clique no nome (perfil público) →
   **Pedir vaga**. Na aba 1 o pedido chega sozinho; aceite. Em **Meus pedidos** do Lucas: PIN, Pix com
   QR Code, **Compartilhar viagem** e **Emergência**.
5. **Foto e autenticador (qualquer conta):** Perfil → **Trocar foto** (a barra do topo muda na hora) →
   **Ativar com aplicativo autenticador** → leia o QR Code com o Google Authenticator do celular → digite o
   código → guarde os códigos de reserva. Saia e entre de novo: depois da senha, o login pede o código.
   No login, **Esqueci minha senha** mostra a recuperação por código.
6. **Admin:** `admin@uvv.br` → Visão geral (KPIs), Usuários (aprovar selo da Marina, remover foto, desligar o
   autenticador de quem perdeu o celular), Denúncias, Alertas (a emergência do passo 4 aparece aqui) e
   **Banco de dados** (diagrama ER gerado ao vivo).

## API

| Recurso | Rotas |
|---|---|
| Autenticação | `POST /api/auth/cadastro`, `/login`, `/login/2fa`, `/logout`, `/verificar-email`, `/reenviar-codigo`, `/solicitar-verificacao`, `/esqueci-senha`, `/redefinir-senha`, `GET/PUT /api/auth/me` |
| Foto de perfil | `PUT/DELETE /api/auth/me/foto` (envio em `multipart/form-data`, campo `foto`), `GET /api/fotos/<token>` |
| Duas etapas | `GET /api/auth/2fa`, `POST /api/auth/2fa/iniciar`, `/ativar`, `/desativar`, `/codigos-reserva` |
| Usuários | `GET /api/usuarios/<id>` (perfil público com reputação) |
| Veículos e contatos | `GET/POST /api/veiculos`, `PUT/DELETE /api/veiculos/<id>`, `GET/POST /api/contatos`, `DELETE /api/contatos/<id>` |
| Caronas | `GET/POST /api/caronas`, `GET /api/caronas/minhas`, `GET /api/caronas/valor-sugerido`, `GET/PUT /api/caronas/<id>`, `POST .../cancelar`, `.../iniciar`, `.../concluir`, `.../posicao` |
| Solicitações | `GET/POST /api/caronas/<id>/solicitacoes`, `GET /api/solicitacoes/minhas`, `POST /api/solicitacoes/<id>/aceitar`, `/recusar`, `/cancelar`, `/embarque`, `/falta` |
| Avaliações e Pix | `GET /api/avaliacoes/pendentes`, `/tags`, `POST /api/solicitacoes/<id>/avaliacao`, `GET .../pix`, `POST .../pagamento` |
| Segurança | `POST /api/caronas/<id>/compartilhar`, `GET /api/acompanhar/<token>` (público), `POST /api/caronas/<id>/sos`, `POST /api/denuncias` |
| Notificações | `GET /api/notificacoes`, `GET /api/notificacoes/contagem`, `POST /api/notificacoes/lidas` |
| Admin | `GET /api/admin/resumo`, `/usuarios`, `/denuncias`, `/alertas`, `/configuracoes`, `/banco` e ações de moderação (verificar, suspender, `DELETE .../foto`, `POST .../resetar-2fa`) |

Rotas protegidas usam o cabeçalho `Authorization: Bearer <token>`. Lista completa: `flask --app app.py routes`.

Todo erro volta em JSON no formato `{"error": "mensagem"}`; erros de validação trazem também
`{"campos": {"email": "Use seu e-mail institucional (@uvv.br)..."}}`, que o front mostra embaixo do campo certo.
Cada requisição é registrada no log com método, rota, status e tempo (`LOG_LEVEL` e `LOG_FILE` no `.env`).

## Regras de negócio

- Só e-mail institucional (`@uvv.br`); oferecer ou pedir carona exige e-mail confirmado.
- Uma carona não pode ter mais passageiros aceitos do que vagas; quando lota, fica `lotada` e sai da busca.
- O motorista não pode pedir vaga na própria carona, e o passageiro não pode pedir a mesma carona duas vezes.
- Não é possível criar carona com data/hora no passado; o rateio tem teto (padrão R$ 5,00, configurável).
- Cancelar uma carona cancela as solicitações em aberto e avisa os passageiros.
- Pedido sem resposta expira 2 h antes da saída (ou ao iniciar a viagem).
- A viagem pode ser iniciada a partir de 30 min antes da saída e precisa de ao menos um passageiro confirmado.
- Embarque só com o PIN certo; passageiro confirmado que não aparece recebe falta.
- Avaliação só depois da carona concluída, uma por pessoa, em até 14 dias; nota escondida até os dois avaliarem ou 7 dias.
- Só denuncia quem dividiu uma carona; o link da família para de funcionar quando a viagem termina.
- Login bloqueia por 10 min após 5 senhas erradas; código de e-mail aceita 5 tentativas e vence em 30 min.
- Senhas com hash (Werkzeug/scrypt); o código de verificação é guardado como HMAC-SHA256, nunca em texto.
- Foto de perfil: só JPG, PNG ou WebP (conferido pelo conteúdo do arquivo), até 512 KB e 1024 px de lado; o
  navegador já envia recortada em 400 × 400.
- Verificação em duas etapas: cada código vale uma vez; 5 códigos errados bloqueiam por 10 min; ligar, desligar ou
  gerar novos códigos de reserva exige a senha e um código; os códigos de reserva ficam só como HMAC.
- Esqueci minha senha: código de 6 números, vale 30 min, 5 tentativas, um pedido por minuto; a resposta é a
  mesma exista a conta ou não. Trocar ou redefinir a senha encerra os logins dos outros aparelhos.

## Banco de dados

17 tabelas, documentadas em [`docs/banco_de_dados.md`](docs/banco_de_dados.md) (gerado com `invoke docsdb`).
Para ver o diagrama: no painel admin, aba **Banco de dados** (gerado ao vivo dos modelos), ou cole
[`docs/banco.dbml`](docs/banco.dbml) em [dbdiagram.io](https://dbdiagram.io).
