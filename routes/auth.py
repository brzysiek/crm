"""Logowanie: hasło, kod z maila (drugi składnik) i odzyskiwanie hasła.

Kolejność jest tu całą ochroną: `session['user_id']` — jedyny klucz, który `require_login`
uznaje — zapada dopiero po poprawnym kodzie. Między hasłem a kodem w sesji leży wyłącznie
`pending_2fa`, który nie otwiera żadnego widoku.
"""
from datetime import datetime, timedelta

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)

from models.auth_token import (CODE_TTL_MINUTES, MAX_ATTEMPTS, RESEND_INTERVAL_SECONDS,
                               RESET_TTL_MINUTES, consume_login_code, consume_reset_token,
                               invalidate_user_tokens, issue_login_code, issue_password_reset,
                               peek_reset_token)

bp = Blueprint('auth', __name__)

MIN_PASSWORD_LENGTH = 8

CODE_ERRORS = {
    'invalid': 'Nieprawidłowy kod. Sprawdź wiadomość i spróbuj ponownie.',
    'expired': f'Kod stracił ważność (po {CODE_TTL_MINUTES} min). Wyślij nowy.',
    'missing': 'Kod wygasł albo został już użyty. Wyślij nowy.',
}


def _two_factor_enabled(user: dict) -> bool:
    """Drugi składnik wymaga dwóch rzeczy: adresu, na który poleci kod, i działającej wysyłki.
    Bez nich nie ma czego włączać — zamiast tego zostawiamy samo hasło i mówimy o tym w logu,
    żeby cicha utrata drugiego składnika nie wyglądała jak normalne logowanie."""
    from models.settings import get_setting
    from services.mailer import is_configured

    if get_setting('login_2fa', 'on') == 'off':
        return False
    if not user.get('email'):
        current_app.logger.warning('2FA pominięte: użytkownik %s nie ma adresu e-mail.',
                                   user['username'])
        return False
    if not is_configured():
        current_app.logger.warning('2FA pominięte: brak konfiguracji wysyłki e-mail.')
        return False
    return True


def _finish_login(user: dict, remember: bool):
    """Nowa sesja od zera — przeniesienie czegokolwiek z sesji sprzed logowania byłoby
    zaproszeniem do podszycia się pod identyfikator nadany wcześniej (session fixation)."""
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['full_name'] = user.get('full_name') or user['username']
    if remember:
        session.permanent = True
    return redirect(url_for('gtd.day'))


def _send_code(user: dict) -> bool:
    from services.auth_mail import send_login_code
    try:
        send_login_code(user, issue_login_code(user['id'], request.remote_addr))
        return True
    except Exception as e:
        current_app.logger.error('Nie udało się wysłać kodu logowania: %s', e)
        return False


def _masked_email(email: str) -> str:
    """W kroku kodu pokazujemy, dokąd poleciał, ale nie cały adres — ekran widzi też ten,
    kto zna samo hasło."""
    name, _, domain = (email or '').partition('@')
    if not domain:
        return ''
    head = name[:2] if len(name) > 3 else name[:1]
    return f'{head}{"•" * 4}@{domain}'


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('gtd.day'))

    error = None
    if request.method == 'POST':
        username = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        from models.user import verify_password
        user = verify_password(username, password)
        if user:
            if not _two_factor_enabled(user):
                return _finish_login(user, remember)
            if _send_code(user):
                session.clear()
                session['pending_2fa'] = {
                    'user_id': user['id'],
                    'email': user.get('email'),
                    'remember': remember,
                    'started_at': datetime.now().isoformat(timespec='seconds'),
                    'sent_at': datetime.now().isoformat(timespec='seconds'),
                }
                return redirect(url_for('auth.login_code'))
            error = ('Nie udało się wysłać kodu na e-mail. Spróbuj ponownie za chwilę '
                     'albo sprawdź Ustawienia → Integracje → E-mail.')
        else:
            error = 'Nieprawidłowy login lub hasło.'

    return render_template('auth/login.html', error=error)


def _pending():
    """Oczekujące logowanie żyje dokładnie tyle, co kod — potem wraca się do hasła."""
    pending = session.get('pending_2fa')
    if not pending:
        return None
    started = datetime.fromisoformat(pending['started_at'])
    if datetime.now() - started > timedelta(minutes=CODE_TTL_MINUTES):
        session.pop('pending_2fa', None)
        return None
    return pending


@bp.route('/login/kod', methods=['GET', 'POST'])
def login_code():
    pending = _pending()
    if not pending:
        return redirect(url_for('auth.login'))

    error = None
    if request.method == 'POST':
        result = consume_login_code(pending['user_id'], request.form.get('code', ''))
        if result == 'ok':
            from models.user import get_user_by_id
            user = get_user_by_id(pending['user_id'])
            session.pop('pending_2fa', None)
            if user and user['is_active']:
                return _finish_login(user, pending['remember'])
            flash('To konto jest nieaktywne.', 'error')
            return redirect(url_for('auth.login'))
        if result == 'blocked':
            session.pop('pending_2fa', None)
            flash(f'Przekroczono limit prób ({MAX_ATTEMPTS}). Zaloguj się jeszcze raz, '
                  'żeby dostać nowy kod.', 'error')
            return redirect(url_for('auth.login'))
        error = CODE_ERRORS.get(result, CODE_ERRORS['invalid'])

    return render_template('auth/code.html', error=error,
                           masked_email=_masked_email(pending.get('email')),
                           can_resend=_can_resend(pending))


def _can_resend(pending: dict) -> bool:
    sent = datetime.fromisoformat(pending['sent_at'])
    return datetime.now() - sent >= timedelta(seconds=RESEND_INTERVAL_SECONDS)


@bp.route('/login/kod/ponow', methods=['POST'])
def resend_code():
    pending = _pending()
    if not pending:
        return redirect(url_for('auth.login'))
    if not _can_resend(pending):
        flash('Nowy kod można wysłać raz na minutę.', 'error')
        return redirect(url_for('auth.login_code'))

    from models.user import get_user_by_id
    user = get_user_by_id(pending['user_id'])
    if user and _send_code(user):
        pending['sent_at'] = datetime.now().isoformat(timespec='seconds')
        session['pending_2fa'] = pending
        flash('Wysłaliśmy nowy kod.', 'success')
    else:
        flash('Nie udało się wysłać kodu. Spróbuj ponownie za chwilę.', 'error')
    return redirect(url_for('auth.login_code'))


@bp.route('/login/zapomniane-haslo', methods=['GET', 'POST'])
def forgot_password():
    if request.method != 'POST':
        return render_template('auth/forgot.html')

    from models.user import get_user_by_login_or_email
    from services.auth_mail import send_password_reset

    user = get_user_by_login_or_email(request.form.get('identifier', ''))
    if user and user['is_active'] and user.get('email'):
        try:
            token = issue_password_reset(user['id'], request.remote_addr)
            send_password_reset(user, url_for('auth.reset_password', token=token, _external=True))
        except Exception as e:
            current_app.logger.error('Nie udało się wysłać linku do resetu hasła: %s', e)
    else:
        current_app.logger.warning('Reset hasła dla nieznanego konta: %s',
                                   request.form.get('identifier', '')[:64])
    # Zawsze ta sama odpowiedź — inaczej formularz stałby się listą istniejących kont.
    return render_template('auth/forgot.html', sent=True)


@bp.route('/login/nowe-haslo/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if peek_reset_token(token) is None:
        return render_template('auth/reset.html', invalid=True,
                               validity_minutes=RESET_TTL_MINUTES)

    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        if len(password) < MIN_PASSWORD_LENGTH:
            error = f'Hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków.'
        elif password != password2:
            error = 'Hasła nie są identyczne.'
        else:
            user_id = consume_reset_token(token)
            if user_id is None:
                return render_template('auth/reset.html', invalid=True,
                                       validity_minutes=RESET_TTL_MINUTES)
            from models.user import change_password
            change_password(user_id, password)
            invalidate_user_tokens(user_id)
            session.clear()
            flash('Hasło zostało zmienione. Zaloguj się nowym hasłem.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset.html', error=error, token=token,
                           min_length=MIN_PASSWORD_LENGTH)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
