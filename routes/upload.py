from flask import Blueprint, request, redirect, url_for, current_app, send_from_directory
import os

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
