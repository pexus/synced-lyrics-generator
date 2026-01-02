import io
import os

from flask import Blueprint, render_template, send_file, send_from_directory
from flask_login import current_user, login_required

from models import Track
from utils.lyrics_format import ensure_srt_indices
from utils.storage import build_user_path, get_user_dir

files_bp = Blueprint('files', __name__)


@files_bp.route('/download_lrc/<basename>')
@login_required
def download_lrc(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    lrc_folder = get_user_dir(current_user.id, 'lrc_output')
    return send_from_directory(lrc_folder, basename + '.lrc', as_attachment=True)


@files_bp.route('/download_ai_lrc/<basename>')
@login_required
def download_ai_lrc(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    lrc_folder = get_user_dir(current_user.id, 'ai_lrc_output')
    return send_from_directory(lrc_folder, basename + '.lrc', as_attachment=True)


@files_bp.route('/download_srt/<basename>')
@login_required
def download_srt(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    srt_folder = get_user_dir(current_user.id, 'srt_output')
    return send_from_directory(srt_folder, basename + '.srt', as_attachment=True)


@files_bp.route('/download_ai_srt/<basename>')
@login_required
def download_ai_srt(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    srt_folder = get_user_dir(current_user.id, 'ai_srt_output')
    return send_from_directory(srt_folder, basename + '.srt', as_attachment=True)


@files_bp.route('/download_srt_numbered/<basename>')
@login_required
def download_srt_numbered(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    srt_path = build_user_path(current_user.id, 'srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return "SRT file not found.", 404
    with open(srt_path, 'r') as file_handle:
        content = file_handle.read()
    numbered = ensure_srt_indices(content)
    download_name = basename + '_numbered.srt'
    return send_file(
        io.BytesIO(numbered.encode('utf-8')),
        as_attachment=True,
        download_name=download_name,
        mimetype='application/x-subrip',
    )


@files_bp.route('/download_ai_srt_numbered/<basename>')
@login_required
def download_ai_srt_numbered(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404
    srt_path = build_user_path(current_user.id, 'ai_srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return "SRT file not found.", 404
    with open(srt_path, 'r') as file_handle:
        content = file_handle.read()
    numbered = ensure_srt_indices(content)
    download_name = basename + '_numbered_ai.srt'
    return send_file(
        io.BytesIO(numbered.encode('utf-8')),
        as_attachment=True,
        download_name=download_name,
        mimetype='application/x-subrip',
    )


@files_bp.route('/debug/lrc/<basename>')
@login_required
def debug_lrc(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    lrc_path = build_user_path(current_user.id, 'lrc_output', basename + '.lrc')
    if not os.path.exists(lrc_path):
        return render_template('lrc_error.html', basename=basename, lrc_path=lrc_path), 404

    with open(lrc_path, 'r') as f:
        content = f.read()

    if not content.strip():
        stats = os.stat(lrc_path)
        return render_template(
            'lrc_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            lrc_path=lrc_path,
        )

    return render_template(
        'lrc_content.html',
        basename=basename,
        content=content,
        source_label='Manual',
    )


@files_bp.route('/debug/ai/lrc/<basename>')
@login_required
def debug_ai_lrc(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    lrc_path = build_user_path(current_user.id, 'ai_lrc_output', basename + '.lrc')
    if not os.path.exists(lrc_path):
        return render_template('lrc_error.html', basename=basename, lrc_path=lrc_path), 404

    with open(lrc_path, 'r') as f:
        content = f.read()

    if not content.strip():
        stats = os.stat(lrc_path)
        return render_template(
            'lrc_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            lrc_path=lrc_path,
        )

    return render_template(
        'lrc_content.html',
        basename=basename,
        content=content,
        source_label='AI',
        download_endpoint='files.download_ai_lrc',
    )


@files_bp.route('/debug/srt/<basename>')
@login_required
def debug_srt(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    srt_path = build_user_path(current_user.id, 'srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return render_template('srt_error.html', basename=basename, srt_path=srt_path), 404

    with open(srt_path, 'r') as f:
        content = f.read()

    if not content.strip():
        stats = os.stat(srt_path)
        return render_template(
            'srt_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            srt_path=srt_path,
        )

    return render_template(
        'srt_content.html',
        basename=basename,
        content=content,
        numbered=False,
        source_label='Manual',
    )


@files_bp.route('/debug/srt_numbered/<basename>')
@login_required
def debug_srt_numbered(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    srt_path = build_user_path(current_user.id, 'srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return render_template('srt_error.html', basename=basename, srt_path=srt_path), 404

    with open(srt_path, 'r') as file_handle:
        content = file_handle.read()

    if not content.strip():
        stats = os.stat(srt_path)
        return render_template(
            'srt_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            srt_path=srt_path,
        )

    numbered = ensure_srt_indices(content)
    return render_template(
        'srt_content.html',
        basename=basename,
        content=numbered,
        numbered=True,
        source_label='Manual',
    )


@files_bp.route('/debug/ai/srt/<basename>')
@login_required
def debug_ai_srt(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    srt_path = build_user_path(current_user.id, 'ai_srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return render_template('srt_error.html', basename=basename, srt_path=srt_path), 404

    with open(srt_path, 'r') as file_handle:
        content = file_handle.read()

    if not content.strip():
        stats = os.stat(srt_path)
        return render_template(
            'srt_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            srt_path=srt_path,
        )

    return render_template(
        'srt_content.html',
        basename=basename,
        content=content,
        numbered=False,
        source_label='AI',
        download_raw_endpoint='files.download_ai_srt',
        download_numbered_endpoint='files.download_ai_srt_numbered',
        view_raw_endpoint='files.debug_ai_srt',
        view_numbered_endpoint='files.debug_ai_srt_numbered',
    )


@files_bp.route('/debug/ai/srt_numbered/<basename>')
@login_required
def debug_ai_srt_numbered(basename):
    track = Track.query.filter_by(user_id=current_user.id, basename=basename).first()
    if not track:
        return "Track not found.", 404

    srt_path = build_user_path(current_user.id, 'ai_srt_output', basename + '.srt')
    if not os.path.exists(srt_path):
        return render_template('srt_error.html', basename=basename, srt_path=srt_path), 404

    with open(srt_path, 'r') as file_handle:
        content = file_handle.read()

    if not content.strip():
        stats = os.stat(srt_path)
        return render_template(
            'srt_empty.html',
            basename=basename,
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            srt_path=srt_path,
        )

    numbered = ensure_srt_indices(content)
    return render_template(
        'srt_content.html',
        basename=basename,
        content=numbered,
        numbered=True,
        source_label='AI',
        download_raw_endpoint='files.download_ai_srt',
        download_numbered_endpoint='files.download_ai_srt_numbered',
        view_raw_endpoint='files.debug_ai_srt',
        view_numbered_endpoint='files.debug_ai_srt_numbered',
    )
