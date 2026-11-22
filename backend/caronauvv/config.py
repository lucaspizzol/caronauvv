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


def _url_banco(padrao: str) -> str:
    """
    Le DATABASE_URL e ajusta o driver do PostgreSQL:
    postgres://... ou postgresql://...  ->  postgresql+psycopg://... (psycopg 3)
    """
    url = os.getenv("DATABASE_URL", "").strip() or padrao
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-caronauvv")

    # SQLite para desenvolvimento local: o arquivo e criado em instance/caronauvv.db.
    # Em producao (Render/Railway) basta definir DATABASE_URL com o PostgreSQL.
    SQLALCHEMY_DATABASE_URI = _url_banco("sqlite:///caronauvv.db")
    # pool_pre_ping: reconecta sozinho se o PostgreSQL derrubar a conexao ociosa
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Validade do token de login (segundos). Padrao: 7 dias.
    TOKEN_MAX_AGE = int(os.getenv("TOKEN_MAX_AGE", 7 * 24 * 60 * 60))

    # Origens liberadas no CORS (frontend Vue). Varias separadas por virgula.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

    # Nivel do log da aplicacao: DEBUG, INFO, WARNING, ERROR
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    DEBUG = _bool("FLASK_DEBUG", True)

    # Log tambem em arquivo (logs/caronauvv.log, com rotacao). Vazio = so no terminal.
    LOG_FILE = os.getenv("LOG_FILE", "")

    # ------------------------------------------------------
    # CADASTRO: so e-mails institucionais (aceita subdominios, ex.: aluno.uvv.br)
    # ------------------------------------------------------
    DOMINIOS_EMAIL = tuple(d.strip().lower() for d in os.getenv("DOMINIOS_EMAIL", "uvv.br").split(",") if d.strip())

    # Validade do codigo de verificacao enviado por e-mail (minutos)
    CODIGO_VALIDADE_MIN = int(os.getenv("CODIGO_VALIDADE_MIN", 30))

    # Sem servidor de e-mail, a API devolve o codigo na resposta ("codigo_dev")
    # para a demonstracao funcionar. NUNCA ligue isso em producao.
    MOSTRAR_CODIGO_DEV = _bool("MOSTRAR_CODIGO_DEV", DEBUG)

    # ------------------------------------------------------
    # E-MAIL (SMTP). Sem MAIL_SERVER, os e-mails so aparecem no log.
    # ------------------------------------------------------
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")

    # Protecao contra forca bruta no login: N erros em X minutos bloqueiam o login
    LOGIN_MAX_TENTATIVAS = int(os.getenv("LOGIN_MAX_TENTATIVAS", 5))
    LOGIN_JANELA_MIN = int(os.getenv("LOGIN_JANELA_MIN", 10))


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    LOG_LEVEL = "WARNING"
    LOG_FILE = ""
    MOSTRAR_CODIGO_DEV = True
    MAIL_SERVER = ""
    PASSWORD_HASH_METHOD = "pbkdf2:sha256:1000"  # so nos testes: hash leve para a suite rodar rapido
