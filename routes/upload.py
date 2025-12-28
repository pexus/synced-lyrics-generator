from flask import Blueprint, request, redirect, url_for, current_app, send_from_directory
import os
from werkzeug.utils import secure_filename
from utils.file_utils import remove_from_processed_files

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    AUDIO_INPUT_FOLDER = current_app.config['AUDIO_INPUT_FOLDER']
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    try:
        if 'audio_file' not in request.files or 'lyrics_file' not in request.files:
            return "Missing audio or lyrics files", 400
        audio_file = request.files['audio_file']
        lyrics_file = request.files['lyrics_file']
        if audio_file.filename == '' or lyrics_file.filename == '':
            return "No files selected", 400
        if not (audio_file.filename.lower().endswith(('.mp3', '.wav'))):
            return "Invalid audio file type. Please use MP3 or WAV files.", 400
        if not lyrics_file.filename.lower().endswith('.txt'):
            return "Invalid lyrics file type. Please use TXT files.", 400
        audio_path = os.path.join(AUDIO_INPUT_FOLDER, audio_file.filename)
        audio_file.save(audio_path)
        base_name = os.path.splitext(audio_file.filename)[0]
        lyrics_filename = base_name + '.txt'
        lyrics_path = os.path.join(LYRICS_INPUT_FOLDER, lyrics_filename)
        lyrics_file.save(lyrics_path)
        return redirect(url_for('main.index'))
    except Exception as e:
        return f"Error uploading files: {str(e)}", 500

@upload_bp.route('/upload_lyrics_for/<basename>', methods=['POST'])
def upload_lyrics_for(basename):
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    if 'lyrics_file' in request.files:
        file = request.files['lyrics_file']
        if file.filename != '':
            lyrics_filename = basename + '.txt'
            file.save(os.path.join(LYRICS_INPUT_FOLDER, lyrics_filename))
    return redirect(url_for('main.index'))

@upload_bp.route('/serve_audio/<filename>')
def serve_audio(filename):
    AUDIO_INPUT_FOLDER = current_app.config['AUDIO_INPUT_FOLDER']
    return send_from_directory(AUDIO_INPUT_FOLDER, filename)

@upload_bp.route('/delete_song/<basename>', methods=['DELETE'])
def delete_song(basename):
    safe_basename = secure_filename(basename)
    if not safe_basename or safe_basename != basename:
        return {"status": "error", "message": "Invalid song name."}, 400

    AUDIO_INPUT_FOLDER = current_app.config['AUDIO_INPUT_FOLDER']
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    LRC_OUTPUT_FOLDER = current_app.config['LRC_OUTPUT_FOLDER']
    SRT_OUTPUT_FOLDER = current_app.config['SRT_OUTPUT_FOLDER']

    errors = []

    for ext in ('.mp3', '.wav'):
        audio_path = os.path.join(AUDIO_INPUT_FOLDER, safe_basename + ext)
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError as exc:
                errors.append(str(exc))

    file_targets = [
        (LYRICS_INPUT_FOLDER, '.txt'),
        (LRC_OUTPUT_FOLDER, '.lrc'),
        (SRT_OUTPUT_FOLDER, '.srt'),
    ]
    for folder, ext in file_targets:
        path = os.path.join(folder, safe_basename + ext)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                errors.append(str(exc))

    try:
        remove_from_processed_files(safe_basename)
    except OSError as exc:
        errors.append(str(exc))

    if errors:
        return {"status": "error", "message": "; ".join(errors)}, 500

    return {"status": "success"}
