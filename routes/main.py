from flask import Blueprint, render_template, request, current_app
from math import ceil
import os
from utils.file_utils import get_processed_files

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    AUDIO_INPUT_FOLDER = current_app.config['AUDIO_INPUT_FOLDER']
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    LRC_OUTPUT_FOLDER = current_app.config['LRC_OUTPUT_FOLDER']
    SRT_OUTPUT_FOLDER = current_app.config['SRT_OUTPUT_FOLDER']
    page = request.args.get('page', 1, type=int)
    per_page = 10
    processed_basenames = get_processed_files()
    all_audio_files = sorted([f for f in os.listdir(AUDIO_INPUT_FOLDER) if f.endswith(('.mp3', '.wav'))])
    lyrics_files_set = set(os.listdir(LYRICS_INPUT_FOLDER))
    total_songs = len(all_audio_files)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_audio_files = all_audio_files[start:end]
    all_audio_statuses = []
    for audio_file in paginated_audio_files:
        base_name = os.path.splitext(audio_file)[0]
        lyrics_file = base_name + '.txt'
        lrc_path = os.path.join(LRC_OUTPUT_FOLDER, base_name + '.lrc')
        srt_path = os.path.join(SRT_OUTPUT_FOLDER, base_name + '.srt')
        is_processed = base_name in processed_basenames
        if is_processed:
            lrc_exists = os.path.exists(lrc_path) and os.path.getsize(lrc_path) > 0
            srt_exists = os.path.exists(srt_path) and os.path.getsize(srt_path) > 0
            is_processed = lrc_exists and srt_exists
        all_audio_statuses.append({
            'audio': audio_file,
            'basename': base_name,
            'lyrics': lyrics_file,
            'has_lyrics': lyrics_file in lyrics_files_set,
            'is_processed': is_processed
        })
    total_pages = ceil(total_songs / per_page)
    return render_template('index.html', 
                           all_audio_statuses=all_audio_statuses,
                           page=page,
                           total_pages=total_pages)
