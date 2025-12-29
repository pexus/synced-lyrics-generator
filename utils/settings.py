from extensions import db
from models import Setting


def get_setting(key, default=None):
    setting = Setting.query.filter_by(key=key).first()
    if setting is None:
        return default
    return setting.value


def get_int_setting(key, default=None):
    value = get_setting(key, default)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def set_setting(key, value):
    setting = Setting.query.filter_by(key=key).first()
    if setting is None:
        setting = Setting(key=key, value=str(value))
        db.session.add(setting)
    else:
        setting.value = str(value)
    db.session.commit()
    return setting


def ensure_setting(key, value):
    setting = Setting.query.filter_by(key=key).first()
    if setting is None:
        setting = Setting(key=key, value=str(value))
        db.session.add(setting)
        db.session.commit()
    return setting
