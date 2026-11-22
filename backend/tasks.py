import os
import sys

from invoke import task

# Usa sempre o Python que esta rodando o invoke (o do .venv) com "python -m ...".
# Assim funciona mesmo em PCs onde o Windows bloqueia os .exe do .venv\Scripts
# (Device Guard / Smart App Control), como flask.exe e pytest.exe.
PY = f'"{sys.executable}"'
FLASK = f"{PY} -m flask --app app.py"


@task
def install(c):
    """Instala o projeto em modo editavel, com dependencias de dev e teste."""
    c.run(f"{PY} -m pip install -e .[dev,test]", echo=True)


@task
def createdb(c):
    """Cria/atualiza as tabelas em instance/caronauvv.db pela migracao."""
    c.run(f"{FLASK} db upgrade", echo=True)


@task
def seed(c):
    """Insere configuracoes padrao e dados de exemplo (senha de todos: 123456)."""
    c.run(f"{FLASK} seed-db", echo=True)


@task
def resetdb(c):
    """Apaga o banco local e recria do zero, ja com os dados de exemplo."""
    if os.path.exists("instance/caronauvv.db"):
        os.remove("instance/caronauvv.db")
    createdb(c)
    seed(c)


@task
def resetvercel(c):
    """
    Zera o banco ONLINE (Neon da Vercel) e recria com os dados de exemplo.
    Precisa da CLI da Vercel logada e desta pasta vinculada ao projeto (.vercel/).
    Use logo antes de apresentar: a carona "de hoje" sai 20 min depois disto.
    """
    import tempfile

    arquivo = os.path.join(tempfile.gettempdir(), "caronauvv_vercel.env")
    try:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta com .vercel/
        with c.cd(raiz):
            c.run(f'vercel env pull "{arquivo}" --environment production --yes', hide=True, echo=False)
        with open(arquivo, encoding="utf-8") as f:
            valores = dict(
                linha.strip().split("=", 1) for linha in f if "=" in linha and not linha.startswith("#")
            )
        url = (valores.get("DATABASE_URL_UNPOOLED") or valores.get("DATABASE_URL") or "").strip('"')
        if not url:
            raise SystemExit("DATABASE_URL nao encontrado nas variaveis da Vercel.")
        env = {"DATABASE_URL": url, "FLASK_DEBUG": "0"}
        print("Zerando o banco online...")
        c.run(f"{FLASK} db downgrade base", env=env, hide=True)
        c.run(f"{FLASK} db upgrade", env=env, hide=True)
        c.run(f"{FLASK} seed-db", env=env)
    finally:
        if os.path.exists(arquivo):
            os.remove(arquivo)  # o arquivo tem a senha do banco: nao deixa no disco


@task
def run(c):
    """Sobe a API em http://localhost:5000 (o mesmo que flask run)."""
    c.run(f"{FLASK} run", echo=True, pty=False)


@task
def docsdb(c):
    """Regera docs/banco_de_dados.md, docs/banco.dbml e docs/schema_postgresql.sql."""
    c.run(f"{PY} scripts/gerar_docs_banco.py", echo=True)


@task
def test(c):
    """Roda os testes do back-end."""
    c.run(f"{PY} -m pytest", echo=True)


@task
def docs(c):
    """Regera docs/CaronaUVV_Documentacao.html e o PDF (precisa do Edge ou Chrome)."""
    c.run(f"{PY} scripts/gerar_documentacao.py --pdf", echo=True)
