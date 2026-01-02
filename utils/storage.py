import os

from flask import current_app


USER_FOLDERS = (
    'audio_input',
    'vocal_input',
    'lyrics_input',
    'lrc_output',
    'srt_output',
    'ai_drafts',
    'ai_lrc_output',
    'ai_srt_output',
)


def get_user_root(user_id):
    storage_root = current_app.config['STORAGE_ROOT']
    return os.path.join(storage_root, f'user_{user_id}')


def get_user_dir(user_id, folder):
    return os.path.join(get_user_root(user_id), folder)


def ensure_user_dirs(user_id):
    for folder in USER_FOLDERS:
        os.makedirs(get_user_dir(user_id, folder), exist_ok=True)


def build_user_path(user_id, folder, filename):
    return os.path.join(get_user_dir(user_id, folder), filename)
