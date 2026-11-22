from invoke import task


@task
def install(c):
    """Instala o projeto em modo editavel, com dependencias de dev e teste."""
    c.run("pip install -e .[dev,test]", echo=True)


@task
def createdb(c):
    """Cria/atualiza as tabelas em instance/caronauvv.db pela migracao."""
    c.run("flask --app app.py db upgrade", echo=True)


@task
def seed(c):
    """Insere configuracoes padrao e dados de exemplo (senha de todos: 123456)."""
    c.run("flask --app app.py seed-db", echo=True)


@task
def resetdb(c):
    """Apaga o banco local e recria do zero, ja com os dados de exemplo."""
    import os
    if os.path.exists("instance/caronauvv.db"):
        os.remove("instance/caronauvv.db")
    createdb(c)
    seed(c)


@task
def docsdb(c):
    """Regera docs/banco_de_dados.md, docs/banco.dbml e docs/schema_postgresql.sql."""
    c.run("python scripts/gerar_docs_banco.py", echo=True)


@task
def test(c):
    c.run("pytest", echo=True)


@task
def docs(c):
    """Regera docs/CaronaUVV_Documentacao.html e o PDF (precisa do Edge ou Chrome)."""
    c.run("python scripts/gerar_documentacao.py --pdf", echo=True)
