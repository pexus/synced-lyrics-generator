import os
import sys
import unittest

# Add the parent directory to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from extensions import db
from models import Track, User
from utils.storage import build_user_path, ensure_user_dirs


class RouteTests(unittest.TestCase):
    """Test cases for the Flask routes"""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.app.testing = True

        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            if not user:
                user = User(email='test@example.com', is_admin=True)
                user.set_password('password123')
                db.session.add(user)
                db.session.commit()
            ensure_user_dirs(user.id)

            track = Track.query.filter_by(user_id=user.id, basename='test-song').first()
            if not track:
                track = Track(
                    user_id=user.id,
                    basename='test-song',
                    audio_filename='test-song.wav',
                    lyrics_filename='test-song.txt',
                )
                db.session.add(track)
                db.session.commit()

            lrc_path = build_user_path(user.id, 'lrc_output', 'test-song.lrc')
            srt_path = build_user_path(user.id, 'srt_output', 'test-song.srt')
            if not os.path.exists(lrc_path):
                with open(lrc_path, 'w') as f:
                    f.write('[00:00.00]Test')
            if not os.path.exists(srt_path):
                with open(srt_path, 'w') as f:
                    f.write('00:00:00,000 --> 00:00:02,000\nTest\n')

        self.app.post('/login', data={'email': 'test@example.com', 'password': 'password123'})

    def test_home_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_lrc_debug_route_existing_file(self):
        response = self.app.get('/debug/lrc/test-song')
        self.assertEqual(response.status_code, 200)

    def test_srt_debug_route_existing_file(self):
        response = self.app.get('/debug/srt/test-song')
        self.assertEqual(response.status_code, 200)

    def test_lrc_debug_route_nonexistent_file(self):
        response = self.app.get('/debug/lrc/non_existent_file')
        self.assertEqual(response.status_code, 404)

    def test_srt_debug_route_nonexistent_file(self):
        response = self.app.get('/debug/srt/non_existent_file')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
