import os
import smtplib
from email.message import EmailMessage


def send_invite_email(to_email, invite_url):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
    use_ssl = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')

    if not smtp_host or not smtp_from:
        raise RuntimeError('SMTP is not configured. Set SMTP_HOST and SMTP_FROM.')

    msg = EmailMessage()
    msg['Subject'] = 'Your Synced Lyrics invite'
    msg['From'] = smtp_from
    msg['To'] = to_email
    msg.set_content(
        'You have been invited to Synced Lyrics Generator.\n\n'
        f'Complete your setup here: {invite_url}\n\n'
        'If you did not expect this invite, you can ignore this email.'
    )

    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port)

    try:
        if use_tls and not use_ssl:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
    finally:
        server.quit()
