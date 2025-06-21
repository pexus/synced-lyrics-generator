from flask import Blueprint, request, render_template, current_app
import os
import time
from utils.file_utils import add_to_processed_files

lyrics_bp = Blueprint('lyrics', __name__)

@lyrics_bp.route('/editor/<audio_file>/<lyrics_file>')
def editor(audio_file, lyrics_file):
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    lyrics_path = os.path.join(LYRICS_INPUT_FOLDER, lyrics_file)
    if not os.path.exists(lyrics_path):
        return "Lyrics file not found.", 404
    with open(lyrics_path, 'r') as f:
        all_lines = f.read().splitlines()
    lyrics_lines = [line for line in all_lines if line.strip()]
    blank_lines_count = len(all_lines) - len(lyrics_lines)
    basename = os.path.splitext(audio_file)[0]
    return render_template('editor.html', audio_file=audio_file, lyrics_lines=lyrics_lines, lyrics_file=lyrics_file, basename=basename, blank_lines_removed=blank_lines_count)

@lyrics_bp.route('/save_lyrics', methods=['POST'])
def save_lyrics():
    LYRICS_INPUT_FOLDER = current_app.config['LYRICS_INPUT_FOLDER']
    data = request.get_json()
    filename = data['filename']
    content = data['content']
    filepath = os.path.join(LYRICS_INPUT_FOLDER, filename)
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@lyrics_bp.route('/save_synced_lyrics', methods=['POST'])
def save_synced_lyrics():
    LRC_OUTPUT_FOLDER = current_app.config['LRC_OUTPUT_FOLDER']
    SRT_OUTPUT_FOLDER = current_app.config['SRT_OUTPUT_FOLDER']
    data = request.get_json()
    audio_file = data['audio_file']
    lyrics_data = data['lyrics_data']
    base_name = os.path.splitext(audio_file)[0]
    valid_lyrics_data = [item for item in lyrics_data if item['time'] is not None]
    if not valid_lyrics_data:
        return {'status': 'error', 'message': 'No valid timestamps found. Please try syncing the lyrics again.'}
    lrc_content = ''
    for item in valid_lyrics_data:
        minutes = int(item['time'] / 60)
        seconds = int(item['time'] % 60)
        hundredths = int((item['time'] * 100) % 100)
        lrc_content += f'[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{item["text"]}\n'
    lrc_path = os.path.join(LRC_OUTPUT_FOLDER, base_name + '.lrc')
    with open(lrc_path, 'w') as f:
        f.write(lrc_content)
    srt_content = ''
    for i, item in enumerate(valid_lyrics_data):
        start_time = item['time']
        end_time = valid_lyrics_data[i+1]['time'] if i + 1 < len(valid_lyrics_data) else start_time + 2
        start_h, start_m, start_s, start_ms = int(start_time/3600), int(start_time/60)%60, int(start_time)%60, int(start_time*1000)%1000
        end_h, end_m, end_s, end_ms = int(end_time/3600), int(end_time/60)%60, int(end_time)%60, int(end_time*1000)%1000
        srt_content += f'{i+1}\n'
        srt_content += f'{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n'
        srt_content += f'{item["text"]}\n\n'
    srt_path = os.path.join(SRT_OUTPUT_FOLDER, base_name + '.srt')
    with open(srt_path, 'w') as f:
        f.write(srt_content)
    if lrc_content.strip() and srt_content.strip():
        add_to_processed_files(base_name)
        return {'status': 'success'}
    else:
        return {'status': 'error', 'message': 'Generated files are empty. Please try again.'}
