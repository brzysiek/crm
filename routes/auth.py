from flask import (Blueprint, redirect, render_template,
                   request, session, url_for)

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('agent.index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        from models.user import verify_password
        user = verify_password(username, password)
        if user:
            session.clear()
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['full_name'] = user.get('full_name') or user['username']
            if remember:
                session.permanent = True
            return redirect(url_for('agent.index'))
        error = 'Nieprawidłowy login lub hasło.'

    return render_template('login.html', error=error)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
