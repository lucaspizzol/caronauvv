import os
import time

from flask import Flask, request

from .config import DEV_SECRET_KEY, Config
from .errors import init_app as init_errors
from .extensions import cors, migrate
from .ext.db import db
from .ext.db import init_app as init_db
from .ext.db import register_models
from .logs import init_app as init_logs


# ==========================================================
# APPLICATION FACTORY
# ==========================================================
def _aplicar_fuso(fuso: str) -> None:
    """Faz datetime.now() devolver o horario de Brasilia em servidores em UTC."""
    if fuso and hasattr(time, "tzset"):  # tzset so existe em Linux/Mac (a Vercel e Linux)
        os.environ["TZ"] = fuso
        time.tzset()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _aplicar_fuso(app.config.get("APP_TZ", ""))

    # ----------------------------------------------------------
    # Logging (nivel definido por LOG_LEVEL no .env)
    # ----------------------------------------------------------
    init_logs(app)

    # ----------------------------------------------------------
    # Banco de dados
    # ----------------------------------------------------------
    init_db(app)
    register_models()
    # render_as_batch: o SQLite nao tem ALTER TABLE completo; o Alembic recria a tabela
    migrate.init_app(app, db, render_as_batch=True)

    # ----------------------------------------------------------
    # CORS para o frontend Vue 3 (Vite em localhost:5173)
    # ----------------------------------------------------------
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # ----------------------------------------------------------
    # Blueprints (um por modulo)
    # ----------------------------------------------------------
    from .admin import init_app as init_admin
    from .auth import init_app as init_auth
    from .avaliacoes import init_app as init_avaliacoes
    from .caronas import init_app as init_caronas
    from .lugares import init_app as init_lugares
    from .notificacoes import init_app as init_notificacoes
    from .seguranca import init_app as init_seguranca
    init_auth(app)            # /api/auth, /api/usuarios, /api/veiculos, /api/contatos
    init_caronas(app)         # /api/caronas, /api/solicitacoes
    init_lugares(app)         # /api/lugares (bairros, CEP, ruas, distancia ate a UVV)
    init_avaliacoes(app)      # avaliacoes, reputacao e pagamento Pix
    init_notificacoes(app)    # /api/notificacoes
    init_seguranca(app)       # link da familia, botao de emergencia, denuncias
    init_admin(app)           # /api/admin (painel da administracao)

    # ----------------------------------------------------------
    # Erros -> JSON ({"error": "..."}), inclusive 404/405/500
    # ----------------------------------------------------------
    init_errors(app)

    # ----------------------------------------------------------
    # Cabecalhos de seguranca em toda resposta da API
    # ----------------------------------------------------------
    @app.after_request
    def _cabecalhos_de_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/api") and resposta.mimetype == "application/json":
            # JSON com dados pessoais: nao guarda em cache e nao roda como pagina
            resposta.headers.setdefault("Cache-Control", "no-store")
            resposta.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return resposta

    if app.config["SECRET_KEY"] == DEV_SECRET_KEY and not app.config.get("DEBUG") and not app.config.get("TESTING"):
        app.logger.critical("SECRET_KEY de desenvolvimento em producao! Defina SECRET_KEY no ambiente.")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "message": "CaronaUVV API is running", "banco": db.engine.dialect.name}

    app.logger.info("CaronaUVV API iniciada (banco: %s)", app.config["SQLALCHEMY_DATABASE_URI"].split("@")[-1])
    return app
