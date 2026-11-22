from .routes import tasks_bp

def init_app(app):
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")