import os

from dotenv import load_dotenv

# Le as variaveis do arquivo backend/.env (se existir). Modelo: backend/.env.example
# Variaveis ja definidas no sistema (ex.: no Render/Railway) tem prioridade.
load_dotenv()


def _bool(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-caronauvv")

    # SQLite para desenvolvimento local: o arquivo e criado em instance/caronauvv.db.
    # Em producao (Render/Railway) basta definir DATABASE_URL com o PostgreSQL.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///caronauvv.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Validade do token de login (segundos). Padrao: 7 dias.
    TOKEN_MAX_AGE = int(os.getenv("TOKEN_MAX_AGE", 7 * 24 * 60 * 60))

    # Origens liberadas no CORS (frontend Vue). Varias separadas por virgula.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

    # Nivel do log da aplicacao: DEBUG, INFO, WARNING, ERROR
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    DEBUG = _bool("FLASK_DEBUG", True)


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LOG_LEVEL = "WARNING"
