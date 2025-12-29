import secrets
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import Invite, Track, User
from utils.auth import admin_required
from utils.email_utils import send_invite_email
from utils.settings import get_int_setting, set_setting

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    max_tracks = get_int_setting(
        'max_tracks_per_user',
        current_app.config['MAX_TRACKS_PER_USER_DEFAULT']
    )

    track_counts = dict(
        db.session.query(Track.user_id, func.count(Track.id)).group_by(Track.user_id).all()
    )
    users = User.query.order_by(User.created_at.desc()).all()
    invites = Invite.query.order_by(Invite.created_at.desc()).all()

    return render_template(
        'admin.html',
        users=users,
        invites=invites,
        track_counts=track_counts,
        max_tracks=max_tracks,
        current_time=datetime.utcnow(),
    )


@admin_bp.route('/admin/invite', methods=['POST'])
@login_required
@admin_required
def create_invite():
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', 'user')
    days_valid = request.form.get('days_valid', '7')

    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('admin.dashboard'))

    try:
        days_valid = int(days_valid)
        if days_valid < 1:
            raise ValueError
    except ValueError:
        flash('Invite expiry must be a positive number of days.', 'error')
        return redirect(url_for('admin.dashboard'))

    user = User.query.filter_by(email=email).first()
    if user and user.password_hash:
        flash('User already active. Use password reset instead of invite.', 'error')
        return redirect(url_for('admin.dashboard'))

    if not user:
        user = User(email=email, is_admin=(role == 'admin'))
        db.session.add(user)
    elif role == 'admin':
        user.is_admin = True

    token = secrets.token_urlsafe(32)
    invite = Invite(
        email=email,
        token=token,
        role=role,
        invited_by_id=current_user.id,
        expires_at=Invite.default_expiry(days_valid),
    )
    db.session.add(invite)
    db.session.commit()

    base_url = current_app.config['PUBLIC_BASE_URL'].rstrip('/')
    invite_url = f"{base_url}{url_for('auth.accept_invite', token=token)}"

    try:
        send_invite_email(email, invite_url)
        flash('Invite sent successfully.', 'success')
    except Exception as exc:
        flash(f'Invite created, but email failed: {exc}', 'error')

    flash(f'Invite link: {invite_url}', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/invite/<int:invite_id>/resend', methods=['POST'])
@login_required
@admin_required
def resend_invite(invite_id):
    invite = Invite.query.get_or_404(invite_id)
    base_url = current_app.config['PUBLIC_BASE_URL'].rstrip('/')
    invite_url = f"{base_url}{url_for('auth.accept_invite', token=invite.token)}"

    try:
        send_invite_email(invite.email, invite_url)
        flash('Invite email resent.', 'success')
    except Exception as exc:
        flash(f'Email failed: {exc}', 'error')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/invite/<int:invite_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_invite(invite_id):
    invite = Invite.query.get_or_404(invite_id)
    invite.used_at = datetime.utcnow()
    db.session.commit()
    flash('Invite revoked.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/settings', methods=['POST'])
@login_required
@admin_required
def update_settings():
    max_tracks = request.form.get('max_tracks', '').strip()
    try:
        max_tracks_value = int(max_tracks)
        if max_tracks_value < 1:
            raise ValueError
    except ValueError:
        flash('Max tracks must be a positive number.', 'error')
        return redirect(url_for('admin.dashboard'))

    set_setting('max_tracks_per_user', max_tracks_value)
    flash('Settings updated.', 'success')
    return redirect(url_for('admin.dashboard'))
