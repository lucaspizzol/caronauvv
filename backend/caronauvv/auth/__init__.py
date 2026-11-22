def init_app(app):
    from .routes import bp, bp_veiculos
    app.register_blueprint(bp, url_prefix="/api/auth")
    app.register_blueprint(bp_veiculos, url_prefix="/api/veiculos")
