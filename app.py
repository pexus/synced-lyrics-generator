import datetime
import logging
import os

from dotenv import load_dotenv
from flask import Flask

from extensions import csrf, db, login_manager
from models import User
from routes import register_blueprints
from utils.settings import ensure_setting

load_dotenv()

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(BASE_DIR, 'data')
STORAGE_ROOT = os.environ.get('STORAGE_ROOT') or os.path.join(BASE_DIR, 'storage')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STORAGE_ROOT, exist_ok=True)

load_dotenv(dotenv_path=os.path.join(DATA_DIR, '.env'), override=False)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(DATA_DIR, 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['STORAGE_ROOT'] = STORAGE_ROOT
app.config['PUBLIC_BASE_URL'] = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5000')
app.config['MAX_TRACKS_PER_USER_DEFAULT'] = int(os.environ.get('MAX_TRACKS_PER_USER', '20'))
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['MFA_ISSUER'] = os.environ.get('MFA_ISSUER', 'Synced Lyrics Generator')
app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Register the timestamp_to_datetime Jinja filter
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Register the file_exists Jinja filter
@app.template_filter('file_exists')
def file_exists_filter(filename, folder):
    filepath = os.path.join(folder, filename)
    return os.path.exists(filepath) and os.path.getsize(filepath) > 0


def init_extensions():
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

init_extensions()
register_blueprints(app)

with app.app_context():
    db.create_all()
    ensure_setting('max_tracks_per_user', app.config['MAX_TRACKS_PER_USER_DEFAULT'])

if __name__ == '__main__':
    app.run(debug=True)
