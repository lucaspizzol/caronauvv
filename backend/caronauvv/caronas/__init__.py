def init_app(app):
    from .routes import bp, bp_solicitacoes
    app.register_blueprint(bp, url_prefix="/api/caronas")
    app.register_blueprint(bp_solicitacoes, url_prefix="/api/solicitacoes")
