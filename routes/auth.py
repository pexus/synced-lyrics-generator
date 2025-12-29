import base64
import io
from datetime import datetime

import pyotp
import qrcode
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import Invite, User
from utils.storage import ensure_user_dirs

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.count() > 0:
        return redirect(url_for('auth.login'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not email:
            error = 'Email is required.'
        elif password != confirm or not password:
            error = 'Passwords must match and cannot be empty.'
        else:
            user = User(email=email, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            ensure_user_dirs(user.id)
            login_user(user)
            return redirect(url_for('admin.dashboard'))

    return render_template('setup.html', error=error)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if User.query.count() == 0:
        return redirect(url_for('auth.setup'))
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        totp_code = request.form.get('totp', '').strip()

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            error = 'Invalid email or password.'
        elif not user.is_active:
            error = 'Account is disabled. Contact an admin.'
        elif user.mfa_enabled:
            if not totp_code:
                error = 'MFA code required.'
            else:
                totp = pyotp.TOTP(user.mfa_secret)
                if not totp.verify(totp_code, valid_window=1):
                    error = 'Invalid MFA code.'

        if not error:
            login_user(user)
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            ensure_user_dirs(user.id)
            return redirect(url_for('main.index'))

    return render_template('login.html', error=error)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/accept-invite/<token>', methods=['GET', 'POST'])
def accept_invite(token):
    invite = Invite.query.filter_by(token=token).first()
    if not invite or not invite.is_valid():
        return render_template('invite_invalid.html')

    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        enable_mfa = request.form.get('enable_mfa') == 'on'

        if password != confirm or not password:
            error = 'Passwords must match and cannot be empty.'
        else:
            user = User.query.filter_by(email=invite.email).first()
            if user and user.password_hash:
                error = 'Account already active. Please log in.'
            else:
                if not user:
                    user = User(email=invite.email, is_admin=(invite.role == 'admin'))
                    db.session.add(user)

                user.set_password(password)
                invite.used_at = datetime.utcnow()
                db.session.commit()
                ensure_user_dirs(user.id)
                login_user(user)

                if enable_mfa:
                    return redirect(url_for('auth.mfa_setup'))

                return redirect(url_for('main.index'))

    return render_template('accept_invite.html', invite=invite, error=error)


@auth_bp.route('/account/security', methods=['GET', 'POST'])
@login_required
def account_security():
    error = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'disable_mfa':
            password = request.form.get('password', '')
            if not current_user.check_password(password):
                error = 'Password is incorrect.'
            else:
                current_user.mfa_enabled = False
                current_user.mfa_secret = None
                db.session.commit()
        return render_template('account_security.html', error=error)

    return render_template('account_security.html', error=error)


@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    if current_user.mfa_enabled:
        return redirect(url_for('auth.account_security'))

    pending_secret = session.get('pending_mfa_secret')
    if not pending_secret:
        pending_secret = pyotp.random_base32()
        session['pending_mfa_secret'] = pending_secret

    totp = pyotp.TOTP(pending_secret)
    issuer = current_app.config.get('MFA_ISSUER', 'Synced Lyrics Generator')
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name=issuer)

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode('ascii')

    error = None
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not totp.verify(code, valid_window=1):
            error = 'Invalid code. Please try again.'
        else:
            current_user.mfa_enabled = True
            current_user.mfa_secret = pending_secret
            db.session.commit()
            session.pop('pending_mfa_secret', None)
            return redirect(url_for('auth.account_security'))

    return render_template(
        'mfa_setup.html',
        provisioning_uri=provisioning_uri,
        qr_b64=qr_b64,
        error=error,
    )
