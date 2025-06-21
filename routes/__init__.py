# Registers all blueprints for the app

from .main import main_bp
from .upload import upload_bp
from .lyrics import lyrics_bp
from .files import files_bp

def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(lyrics_bp)
    app.register_blueprint(files_bp)
