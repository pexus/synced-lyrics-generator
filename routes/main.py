import os

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from models import Track
from utils.settings import get_int_setting
from utils.storage import build_user_path, ensure_user_dirs

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    ensure_user_dirs(current_user.id)

    page = request.args.get('page', 1, type=int)
    per_page = 10

    total_tracks = Track.query.filter_by(user_id=current_user.id).count()
    max_tracks = get_int_setting(
        'max_tracks_per_user',
        current_app.config['MAX_TRACKS_PER_USER_DEFAULT']
    )

    start = (page - 1) * per_page
    tracks = (
        Track.query
        .filter_by(user_id=current_user.id)
        .order_by(Track.created_at.desc())
        .offset(start)
        .limit(per_page)
        .all()
    )

    all_audio_statuses = []
    for track in tracks:
        lyrics_path = build_user_path(current_user.id, 'lyrics_input', track.lyrics_filename)
        lrc_path = build_user_path(current_user.id, 'lrc_output', track.basename + '.lrc')
        srt_path = build_user_path(current_user.id, 'srt_output', track.basename + '.srt')
        has_lyrics = bool(os.path.exists(lyrics_path) and os.path.getsize(lyrics_path) > 0)
        lrc_exists = bool(os.path.exists(lrc_path) and os.path.getsize(lrc_path) > 0)
        srt_exists = bool(os.path.exists(srt_path) and os.path.getsize(srt_path) > 0)
        all_audio_statuses.append({
            'audio': track.audio_filename,
            'basename': track.basename,
            'lyrics': track.lyrics_filename,
            'has_lyrics': has_lyrics,
            'is_processed': lrc_exists and srt_exists,
            'lrc_exists': lrc_exists,
            'srt_exists': srt_exists,
        })

    total_pages = max(1, (total_tracks + per_page - 1) // per_page)

    return render_template(
        'index.html',
        all_audio_statuses=all_audio_statuses,
        page=page,
        total_pages=total_pages,
        track_count=total_tracks,
        max_tracks=max_tracks,
    )
