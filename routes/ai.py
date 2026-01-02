import datetime
import json
import os

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Track
from utils.ai_alignment import build_line_timings
from utils.ai_transcription import TranscriptionError, extract_word_timings, transcribe_audio
from utils.lyrics_format import build_lrc_content, build_srt_content
from utils.storage import build_user_path, ensure_user_dirs

ai_bp = Blueprint('ai', __name__)


def load_lyrics_lines(lyrics_path):
    with open(lyrics_path, 'rb') as file_handle:
        raw_bytes = file_handle.read()
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = raw_bytes.decode('cp1252')
        with open(lyrics_path, 'w', encoding='utf-8') as file_handle:
            file_handle.write(text)
    all_lines = text.splitlines()
    lyrics_lines = [line for line in all_lines if line.strip()]
    blank_lines_count = len(all_lines) - len(lyrics_lines)
    return lyrics_lines, blank_lines_count


def load_ai_draft(user_id, basename):
    draft_path = build_user_path(user_id, 'ai_drafts', f'{basename}.json')
    if not os.path.exists(draft_path):
        return None
    with open(draft_path, 'r') as file_handle:
        return json.load(file_handle)


def save_ai_draft(user_id, basename, draft):
    draft_path = build_user_path(user_id, 'ai_drafts', f'{basename}.json')
    with open(draft_path, 'w') as file_handle:
        json.dump(draft, file_handle, indent=2)


def write_ai_outputs(user_id, basename, lyrics_data):
    lrc_content = build_lrc_content(lyrics_data)
    srt_content = build_srt_content(lyrics_data)

    lrc_path = build_user_path(user_id, 'ai_lrc_output', basename + '.lrc')
    with open(lrc_path, 'w') as file_handle:
        file_handle.write(lrc_content)

    srt_path = build_user_path(user_id, 'ai_srt_output', basename + '.srt')
    with open(srt_path, 'w') as file_handle:
        file_handle.write(srt_content)

    return lrc_content, srt_content


def get_vocal_stem_path(user_id, basename):
    for ext in ('.wav', '.mp3'):
        path = build_user_path(user_id, 'vocal_input', f'{basename}_vocals{ext}')
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None


@ai_bp.route('/ai/generate/<basename>', methods=['POST'])
@login_required
def generate_ai_draft(basename):
    ensure_user_dirs(current_user.id)

    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": "Track not found."}, 404
        return "Track not found.", 404

    lyrics_path = build_user_path(current_user.id, 'lyrics_input', track.lyrics_filename)
    audio_path = build_user_path(current_user.id, 'audio_input', track.audio_filename)
    use_vocals_value = (
        request.args.get('use_vocals')
        or request.form.get('use_vocals')
        or (request.get_json(silent=True) or {}).get('use_vocals')
    )
    use_vocals = str(use_vocals_value).lower() in ('1', 'true', 'yes', 'on')
    vocal_path = get_vocal_stem_path(current_user.id, track.basename)
    if use_vocals and vocal_path:
        audio_path = vocal_path

    if not os.path.exists(lyrics_path):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": "Lyrics file not found."}, 404
        return "Lyrics file not found.", 404
    if not os.path.exists(audio_path):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": "Audio file not found."}, 404
        return "Audio file not found.", 404

    lyrics_lines, blank_lines_count = load_lyrics_lines(lyrics_path)
    if not lyrics_lines:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": "Lyrics file is empty after removing blank lines."}, 400
        return "Lyrics file is empty after removing blank lines.", 400

    prompt_lines = lyrics_lines[:8]
    prompt = "Transcribe in romanized (Latin) letters. Match the lyrics when possible.\n"
    prompt += "\n".join(prompt_lines)

    timeout_seconds = current_app.config.get('OPENAI_TRANSCRIBE_TIMEOUT', 300)
    try:
        transcription = transcribe_audio(
            audio_path,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
        )
    except TranscriptionError as exc:
        current_app.logger.exception("AI transcription failed.")
        message = f"AI transcription failed: {exc}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": message}, 500
        return message, 500

    transcript_words = extract_word_timings(transcription)
    if not transcript_words:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"status": "error", "message": "AI transcription did not return word timestamps."}, 500
        return "AI transcription did not return word timestamps.", 500

    line_timings = build_line_timings(lyrics_lines, transcript_words)
    lyrics_data = []
    for line, timing in zip(lyrics_lines, line_timings):
        entry = {'text': line, 'time': timing.get('time')}
        if timing.get('end_time') is not None:
            entry['end_time'] = timing['end_time']
        lyrics_data.append(entry)

    draft = {
        'basename': basename,
        'audio_filename': track.audio_filename,
        'lyrics_filename': track.lyrics_filename,
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'blank_lines_removed': blank_lines_count,
        'source': 'openai-whisper-1',
        'used_vocal_stem': bool(use_vocals and vocal_path),
        'lyrics_data': lyrics_data,
        'original_lyrics_data': lyrics_data,
    }
    save_ai_draft(current_user.id, basename, draft)
    write_ai_outputs(current_user.id, basename, lyrics_data)

    redirect_url = url_for('ai.editor', basename=basename)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success", "redirect": redirect_url}
    return redirect(redirect_url)


@ai_bp.route('/ai/processing/<basename>')
@login_required
def processing(basename):
    ensure_user_dirs(current_user.id)

    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    vocal_available = bool(get_vocal_stem_path(current_user.id, basename))
    return render_template('ai_processing.html', basename=basename, vocal_available=vocal_available)


@ai_bp.route('/ai/editor/<basename>')
@login_required
def editor(basename):
    ensure_user_dirs(current_user.id)

    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    lyrics_path = build_user_path(current_user.id, 'lyrics_input', track.lyrics_filename)
    if not os.path.exists(lyrics_path):
        return "Lyrics file not found.", 404

    lyrics_lines, blank_lines_count = load_lyrics_lines(lyrics_path)
    draft = load_ai_draft(current_user.id, basename)

    if draft and draft.get('lyrics_data'):
        lyrics_data = draft['lyrics_data']
        draft_lines = [item.get('text', '') for item in lyrics_data]
        if draft_lines:
            lyrics_lines = draft_lines
        timestamps = [item.get('time') for item in lyrics_data]
        original_lyrics_data = draft.get('original_lyrics_data') or lyrics_data
    else:
        timestamps = [None for _ in lyrics_lines]
        original_lyrics_data = [
            {'text': line, 'time': None, 'end_time': None}
            for line in lyrics_lines
        ]

    return render_template(
        'ai_editor.html',
        audio_file=track.audio_filename,
        lyrics_lines=lyrics_lines,
        timestamps=timestamps,
        draft_lyrics_data=lyrics_data,
        draft_meta=draft,
        basename=basename,
        blank_lines_removed=blank_lines_count,
        has_draft=bool(draft),
        original_lyrics_data=original_lyrics_data,
    )


@ai_bp.route('/ai/save_draft', methods=['POST'])
@login_required
def save_draft():
    ensure_user_dirs(current_user.id)

    data = request.get_json() or {}
    basename = data.get('basename')
    lyrics_data = data.get('lyrics_data', [])

    if not basename:
        return {"status": "error", "message": "Missing basename."}, 400

    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return {"status": "error", "message": "Track not found."}, 404

    existing = load_ai_draft(current_user.id, basename) or {}
    original_lyrics_data = existing.get('original_lyrics_data') or lyrics_data
    draft = {
        'basename': basename,
        'audio_filename': track.audio_filename,
        'lyrics_filename': track.lyrics_filename,
        'updated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'source': 'openai-whisper-1',
        'lyrics_data': lyrics_data,
        'original_lyrics_data': original_lyrics_data,
    }
    save_ai_draft(current_user.id, basename, draft)
    write_ai_outputs(current_user.id, basename, lyrics_data)

    return {"status": "success"}
