import datetime
import json
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

    def normalize_text(text):
        if not text:
            return ''
        cleaned = re.sub(r"[^\w\s'\-]", '', text.lower())
        return re.sub(r'\s+', ' ', cleaned).strip()

    def entry_times(entry):
        start = entry.get('time')
        if start is None:
            start = entry.get('start')
        end = entry.get('end_time')
        if end is None:
            end = entry.get('end')
        return start, end

    def map_entries_to_lines(entries):
        start_values = [None for _ in lyrics_lines]
        end_values = [None for _ in lyrics_lines]
        if not entries:
            return start_values, end_values
        if len(entries) == len(lyrics_lines):
            for index, entry in enumerate(entries):
                start, end = entry_times(entry)
                start_values[index] = start
                end_values[index] = end
            return start_values, end_values

        entry_index = 0
        for line_index, line in enumerate(lyrics_lines):
            target = normalize_text(line)
            while entry_index < len(entries):
                entry_text = normalize_text(entries[entry_index].get('text'))
                if entry_text == target:
                    start, end = entry_times(entries[entry_index])
                    start_values[line_index] = start
                    end_values[line_index] = end
                    entry_index += 1
                    break
                entry_index += 1
        return start_values, end_values

    start_times = [None for _ in lyrics_lines]
    end_times = [None for _ in lyrics_lines]
    ai_draft_path = build_user_path(current_user.id, 'ai_drafts', basename + '.json')
    ai_draft_available = bool(os.path.exists(ai_draft_path) and os.path.getsize(ai_draft_path) > 0)
    source = request.args.get('source', '').lower()
    use_ai_draft = source == 'ai' and ai_draft_available

    manual_srt_path = build_user_path(current_user.id, 'srt_output', basename + '.srt')
    if use_ai_draft and ai_draft_available:
        with open(ai_draft_path, 'r') as file_handle:
            draft = json.load(file_handle)
        draft_entries = draft.get('lyrics_data') or []
        start_times, end_times = map_entries_to_lines(draft_entries)
    elif os.path.exists(manual_srt_path) and os.path.getsize(manual_srt_path) > 0:
        with open(manual_srt_path, 'r') as file_handle:
            srt_content = file_handle.read()
        cues = parse_srt_content(srt_content)
        if cues:
            start_times, end_times = map_entries_to_lines(cues)

    has_manual_sync = any(time is not None for time in start_times)
    manual_source_label = 'AI Draft' if use_ai_draft and has_manual_sync else None

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
        manual_source_label=manual_source_label,
        ai_draft_available=ai_draft_available,
        ai_draft_loaded=use_ai_draft,
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
