def init_app(app):
    from .routes import bp, bp_contatos, bp_fotos, bp_usuarios, bp_veiculos
    app.register_blueprint(bp, url_prefix="/api/auth")
    app.register_blueprint(bp_veiculos, url_prefix="/api/veiculos")
    app.register_blueprint(bp_usuarios, url_prefix="/api/usuarios")
    app.register_blueprint(bp_contatos, url_prefix="/api/contatos")
    app.register_blueprint(bp_fotos, url_prefix="/api/fotos")
