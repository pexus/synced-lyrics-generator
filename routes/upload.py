import os

from flask import Blueprint, current_app, redirect, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Track
from utils.settings import get_int_setting
from utils.storage import build_user_path, ensure_user_dirs, get_user_dir

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    ensure_user_dirs(current_user.id)

    max_tracks = get_int_setting(
        'max_tracks_per_user',
        current_app.config['MAX_TRACKS_PER_USER_DEFAULT']
    )
    current_count = Track.query.filter_by(user_id=current_user.id).count()
    if max_tracks is not None and current_count >= max_tracks:
        return "Track limit reached. Delete older tracks before uploading new ones.", 400

    try:
        if 'audio_file' not in request.files or 'lyrics_file' not in request.files:
            return "Missing audio or lyrics files", 400

        audio_file = request.files['audio_file']
        lyrics_file = request.files['lyrics_file']

        if audio_file.filename == '' or lyrics_file.filename == '':
            return "No files selected", 400

        audio_filename = secure_filename(audio_file.filename)
        if not audio_filename:
            return "Invalid audio file name.", 400
        if not audio_filename.lower().endswith(('.mp3', '.wav')):
            return "Invalid audio file type. Please use MP3 or WAV files.", 400

        if not lyrics_file.filename.lower().endswith('.txt'):
            return "Invalid lyrics file type. Please use TXT files.", 400

        base_name = os.path.splitext(audio_filename)[0]
        existing_track = Track.query.filter_by(user_id=current_user.id, basename=base_name).first()
        if existing_track:
            return "A track with this name already exists. Delete it before uploading a new one.", 400

        lyrics_filename = base_name + '.txt'
        audio_path = build_user_path(current_user.id, 'audio_input', audio_filename)
        lyrics_path = build_user_path(current_user.id, 'lyrics_input', lyrics_filename)

        audio_file.save(audio_path)
        lyrics_file.save(lyrics_path)

        track = Track(
            user_id=current_user.id,
            basename=base_name,
            audio_filename=audio_filename,
            lyrics_filename=lyrics_filename,
        )
        db.session.add(track)
        db.session.commit()

        return redirect(url_for('main.index'))
    except Exception as exc:
        return f"Error uploading files: {str(exc)}", 500


@upload_bp.route('/upload_lyrics_for/<basename>', methods=['POST'])
@login_required
def upload_lyrics_for(basename):
    ensure_user_dirs(current_user.id)

    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    if 'lyrics_file' in request.files:
        file = request.files['lyrics_file']
        if file.filename != '':
            if not file.filename.lower().endswith('.txt'):
                return "Invalid lyrics file type. Please use TXT files.", 400
            lyrics_filename = track.basename + '.txt'
            file.save(build_user_path(current_user.id, 'lyrics_input', lyrics_filename))
            track.lyrics_filename = lyrics_filename
            db.session.commit()

    return redirect(url_for('main.index'))


@upload_bp.route('/serve_audio/<filename>')
@login_required
def serve_audio(filename):
    track = Track.query.filter_by(user_id=current_user.id, audio_filename=filename).first()
    if not track:
        return "Audio file not found.", 404
    audio_folder = get_user_dir(current_user.id, 'audio_input')
    return send_from_directory(audio_folder, filename)


@upload_bp.route('/delete_song/<basename>', methods=['DELETE'])
@login_required
def delete_song(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return {"status": "error", "message": "Track not found."}, 404

    errors = []

    paths_to_delete = [
        build_user_path(current_user.id, 'audio_input', track.audio_filename),
        build_user_path(current_user.id, 'lyrics_input', track.lyrics_filename),
        build_user_path(current_user.id, 'lrc_output', track.basename + '.lrc'),
        build_user_path(current_user.id, 'srt_output', track.basename + '.srt'),
    ]

    for path in paths_to_delete:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                errors.append(str(exc))

    if errors:
        return {"status": "error", "message": "; ".join(errors)}, 500

    db.session.delete(track)
    db.session.commit()

    return {"status": "success"}
