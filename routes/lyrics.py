import datetime
import os
import re

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Track
from utils.lyrics_format import build_lrc_content, build_srt_content, parse_srt_content
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
    start_times = [None for _ in lyrics_lines]
    end_times = [None for _ in lyrics_lines]
    manual_srt_path = build_user_path(current_user.id, 'srt_output', basename + '.srt')
    if os.path.exists(manual_srt_path) and os.path.getsize(manual_srt_path) > 0:
        with open(manual_srt_path, 'r') as file_handle:
            srt_content = file_handle.read()
        cues = parse_srt_content(srt_content)
        if cues:
            if len(cues) == len(lyrics_lines):
                for index, cue in enumerate(cues):
                    start_times[index] = cue.get('start')
                    end_times[index] = cue.get('end')
            else:
                def normalize_text(text):
                    if not text:
                        return ''
                    cleaned = re.sub(r"[^\w\s'\-]", '', text.lower())
                    return re.sub(r'\s+', ' ', cleaned).strip()

                cue_index = 0
                for line_index, line in enumerate(lyrics_lines):
                    target = normalize_text(line)
                    while cue_index < len(cues):
                        cue_text = normalize_text(cues[cue_index].get('text'))
                        if cue_text == target:
                            start_times[line_index] = cues[cue_index].get('start')
                            end_times[line_index] = cues[cue_index].get('end')
                            cue_index += 1
                            break
                        cue_index += 1

    has_manual_sync = any(time is not None for time in start_times)

    return render_template(
        'editor.html',
        audio_file=audio_file,
        lyrics_lines=lyrics_lines,
        lyrics_file=lyrics_file,
        basename=basename,
        blank_lines_removed=blank_lines_count,
        start_times=start_times,
        end_times=end_times,
        has_manual_sync=has_manual_sync,
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

    if not any(item.get('time') is not None for item in lyrics_data):
        return {
            'status': 'error',
            'message': 'No valid timestamps found. Please try syncing the lyrics again.'
        }

    lrc_content = build_lrc_content(lyrics_data)

    lrc_path = build_user_path(current_user.id, 'lrc_output', track.basename + '.lrc')
    with open(lrc_path, 'w') as f:
        f.write(lrc_content)

    srt_content = build_srt_content(lyrics_data)

    srt_path = build_user_path(current_user.id, 'srt_output', track.basename + '.srt')
    with open(srt_path, 'w') as f:
        f.write(srt_content)

    if lrc_content.strip() and srt_content.strip():
        track.synced_at = datetime.datetime.utcnow()
        db.session.commit()
        return {'status': 'success'}

    return {'status': 'error', 'message': 'Generated files are empty. Please try again.'}
