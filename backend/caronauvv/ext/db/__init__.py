from datetime import datetime, timedelta

import click
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

# Nomes fixos para constraints (pk_, fk_, uq_, ck_, ix_): o Flask-Migrate/Alembic
# precisa deles para conseguir alterar ou remover constraints depois.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))


# ==========================================================
# SQLite: liga a verificacao de chaves estrangeiras
# (vem desligada por padrao; no PostgreSQL ja e sempre ligada)
# ==========================================================
@event.listens_for(Engine, "connect")
def _ligar_foreign_keys_sqlite(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def check_valores(coluna: str, valores: tuple) -> str:
    """Expressao para CheckConstraint: status IN ('ativa', 'lotada', ...)."""
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def init_app(app):
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        """Cria todas as tabelas de uma vez e marca a migracao como aplicada."""
        db.create_all()
        # Registra a versao atual no Alembic: depois disso "flask db upgrade" segue normalmente
        from flask_migrate import stamp
        stamp()
        print(f"Banco criado em: {db.engine.url}")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Insere configuracoes padrao e dados de exemplo (uso: flask --app app.py seed-db)."""
        from .seed import popular_banco
        print(popular_banco())

    @app.cli.command("limpar-gps")
    @click.option("--dias", default=None, type=int, help="Padrao: configuracao dias_guardar_gps (30).")
    def limpar_gps_command(dias):
        """Apaga as trilhas GPS mais antigas que N dias."""
        removidas = limpar_trilhas_gps(dias)
        print(f"{removidas} posicoes GPS apagadas.")


def register_models():
    """
    Importa todos os modulos que definem modelos para que
    sejam registrados no metadata do SQLAlchemy.
    """
    import caronauvv.auth.models          # noqa: F401
    import caronauvv.caronas.models       # noqa: F401
    import caronauvv.avaliacoes.models    # noqa: F401
    import caronauvv.notificacoes.models  # noqa: F401
    import caronauvv.seguranca.models     # noqa: F401
    import caronauvv.admin.models         # noqa: F401


# ==========================================================
# MANUTENCAO: "Trilhas GPS apagadas automaticamente apos 30 dias"
# ==========================================================
def limpar_trilhas_gps(dias: int | None = None) -> int:
    from caronauvv.admin.models import Configuracao
    from caronauvv.caronas.models import PosicaoGps

    if dias is None:
        dias = Configuracao.obter_int("dias_guardar_gps", 30)
    limite = datetime.now() - timedelta(days=dias)
    resultado = db.session.execute(db.delete(PosicaoGps).where(PosicaoGps.registrada_em < limite))
    db.session.commit()
    return resultado.rowcount
