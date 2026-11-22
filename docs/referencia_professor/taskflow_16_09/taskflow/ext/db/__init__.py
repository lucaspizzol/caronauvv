from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)


def register_models():
    """
    Importa todos os modulos que definem modelos para que
    sejam registrados no metadata do SQLAlchemy.
    """
    import taskflow.auth.models
    import taskflow.projects.models
    import taskflow.tasks.models