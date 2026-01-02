# Registers all blueprints for the app

from .admin import admin_bp
from .ai import ai_bp
from .auth import auth_bp
from .files import files_bp
from .lyrics import lyrics_bp
from .main import main_bp
from .upload import upload_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(lyrics_bp)
    app.register_blueprint(files_bp)
