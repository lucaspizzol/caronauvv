from flask import Flask

from .config import Config
from .ext.db import init_app as init_db
from .ext.db import register_models

# ==========================================================
# CARREGAMENTO CENTRALIZADO DE AMBIENTE
# ==========================================================
def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    # ----------------------------------------------------------
    # Inicializacao do banco de dados
    # ----------------------------------------------------------
    init_db(app)

    # ----------------------------------------------------------
    # Registro dos modelos no metadata do SQLAlchemy
    # ----------------------------------------------------------
    register_models()

    return app