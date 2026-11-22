from .routes import projects_bp

def init_app(app):
    app.register_blueprint(projects_bp, url_prefix="/api/projects")