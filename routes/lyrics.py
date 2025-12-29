import datetime
import os

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Track
from utils.storage import build_user_path, ensure_user_dirs

lyrics_bp = Blueprint('lyrics', __name__)


@lyrics_bp.route('/editor/<audio_file>/<lyrics_file>')
@login_required
def editor(audio_file, lyrics_file):
    ensure_user_dirs(current_user.id)

    track = Track.query.filter_by(
        user_id=current_user.id,
        audio_filename=audio_file,
        lyrics_filename=lyrics_file
    ).first()
    if not track:
        return "Track not found.", 404

    lyrics_path = build_user_path(current_user.id, 'lyrics_input', lyrics_file)
    if not os.path.exists(lyrics_path):
        return "Lyrics file not found.", 404

    with open(lyrics_path, 'rb') as f:
        raw_bytes = f.read()
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = raw_bytes.decode('cp1252')
        with open(lyrics_path, 'w', encoding='utf-8') as f:
            f.write(text)
    all_lines = text.splitlines()

    lyrics_lines = [line for line in all_lines if line.strip()]
    blank_lines_count = len(all_lines) - len(lyrics_lines)
    basename = track.basename

    return render_template(
        'editor.html',
        audio_file=audio_file,
        lyrics_lines=lyrics_lines,
        lyrics_file=lyrics_file,
        basename=basename,
        blank_lines_removed=blank_lines_count,
    )


@lyrics_bp.route('/save_lyrics', methods=['POST'])
@login_required
def save_lyrics():
    ensure_user_dirs(current_user.id)

    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content')

    if not filename:
        return {"status": "error", "message": "Missing filename."}, 400

    track = Track.query.filter_by(user_id=current_user.id, lyrics_filename=filename).first()
    if not track:
        return {"status": "error", "message": "Lyrics file not found."}, 404

    filepath = build_user_path(current_user.id, 'lyrics_input', filename)
    try:
        with open(filepath, 'w') as f:
            f.write(content or '')
        return {"status": "success"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}, 500


@lyrics_bp.route('/save_synced_lyrics', methods=['POST'])
@login_required
def save_synced_lyrics():
    ensure_user_dirs(current_user.id)

    data = request.get_json()
    audio_file = data.get('audio_file')
    lyrics_data = data.get('lyrics_data', [])

    if not audio_file:
        return {"status": "error", "message": "Missing audio file."}, 400

    track = Track.query.filter_by(user_id=current_user.id, audio_filename=audio_file).first()
    if not track:
        return {"status": "error", "message": "Track not found."}, 404

    valid_lyrics_data = [item for item in lyrics_data if item.get('time') is not None]
    if not valid_lyrics_data:
        return {
            'status': 'error',
            'message': 'No valid timestamps found. Please try syncing the lyrics again.'
        }

    lrc_content = ''
    for item in valid_lyrics_data:
        minutes = int(item['time'] / 60)
        seconds = int(item['time'] % 60)
        hundredths = int((item['time'] * 100) % 100)
        lrc_content += f'[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{item["text"]}\n'

    lrc_path = build_user_path(current_user.id, 'lrc_output', track.basename + '.lrc')
    with open(lrc_path, 'w') as f:
        f.write(lrc_content)

    srt_content = ''
    for i, item in enumerate(valid_lyrics_data):
        start_time = item['time']
        end_time = valid_lyrics_data[i + 1]['time'] if i + 1 < len(valid_lyrics_data) else start_time + 2
        start_h = int(start_time / 3600)
        start_m = int(start_time / 60) % 60
        start_s = int(start_time) % 60
        start_ms = int(start_time * 1000) % 1000
        end_h = int(end_time / 3600)
        end_m = int(end_time / 60) % 60
        end_s = int(end_time) % 60
        end_ms = int(end_time * 1000) % 1000
        srt_content += (
            f'{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} '
            f'--> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n'
        )
        srt_content += f'{item["text"]}\n\n'

    srt_path = build_user_path(current_user.id, 'srt_output', track.basename + '.srt')
    with open(srt_path, 'w') as f:
        f.write(srt_content)

    if lrc_content.strip() and srt_content.strip():
        track.synced_at = datetime.datetime.utcnow()
        db.session.commit()
        return {'status': 'success'}

    return {'status': 'error', 'message': 'Generated files are empty. Please try again.'}
