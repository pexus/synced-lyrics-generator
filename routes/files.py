from flask import Blueprint, send_from_directory, current_app, render_template
import os
import time

files_bp = Blueprint('files', __name__)

@files_bp.route('/download_lrc/<basename>')
def download_lrc(basename):
    LRC_OUTPUT_FOLDER = current_app.config['LRC_OUTPUT_FOLDER']
    return send_from_directory(LRC_OUTPUT_FOLDER, basename + '.lrc', as_attachment=True)

@files_bp.route('/download_srt/<basename>')
def download_srt(basename):
    SRT_OUTPUT_FOLDER = current_app.config['SRT_OUTPUT_FOLDER']
    return send_from_directory(SRT_OUTPUT_FOLDER, basename + '.srt', as_attachment=True)

@files_bp.route('/debug/lrc/<basename>')
def debug_lrc(basename):
    LRC_OUTPUT_FOLDER = current_app.config['LRC_OUTPUT_FOLDER']
    lrc_path = os.path.join(LRC_OUTPUT_FOLDER, basename + '.lrc')
    if not os.path.exists(lrc_path):
        return render_template('lrc_error.html', basename=basename, lrc_path=lrc_path), 404
    with open(lrc_path, 'r') as f:
        content = f.read()
    if not content.strip():
        stats = os.stat(lrc_path)
        file_size = stats.st_size
        created_time = stats.st_ctime
        modified_time = stats.st_mtime
        return render_template('lrc_empty.html', basename=basename, file_size=file_size, created_time=created_time, modified_time=modified_time, lrc_path=lrc_path)
    return render_template('lrc_content.html', basename=basename, content=content)

@files_bp.route('/debug/srt/<basename>')
def debug_srt(basename):
    SRT_OUTPUT_FOLDER = current_app.config['SRT_OUTPUT_FOLDER']
    srt_path = os.path.join(SRT_OUTPUT_FOLDER, basename + '.srt')
    if not os.path.exists(srt_path):
        return render_template('srt_error.html', basename=basename, srt_path=srt_path), 404
    with open(srt_path, 'r') as f:
        content = f.read()
    if not content.strip():
        stats = os.stat(srt_path)
        file_size = stats.st_size
        created_time = stats.st_ctime
        modified_time = stats.st_mtime
        return render_template('srt_empty.html', basename=basename, file_size=file_size, created_time=created_time, modified_time=modified_time, srt_path=srt_path)
    return render_template('srt_content.html', basename=basename, content=content)
