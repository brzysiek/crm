from flask import (Blueprint, flash, redirect,
                   render_template, request, url_for)

from models.user import (change_password, create_user, delete_user,
                          get_all_users, get_user_by_id, update_user,
                          get_user_by_username)

bp = Blueprint('users', __name__, url_prefix='/settings/users')


@bp.route('/')
def list_users():
    users = get_all_users()
    return render_template('settings/users.html', active_tab='users', users=users)


@bp.route('/new', methods=['POST'])
def new_user():
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'cashier')
    password = request.form.get('password', '')
    password2 = request.form.get('password2', '')

    errors = []
    if not username:
        errors.append('Login jest wymagany.')
    if not full_name:
        errors.append('Imię i nazwisko jest wymagane.')
    if not password:
        errors.append('Hasło jest wymagane.')
    if password != password2:
        errors.append('Hasła nie są identyczne.')
    if not errors and get_user_by_username(username):
        errors.append(f'Login „{username}" jest już zajęty.')

    if errors:
        for e in errors:
            flash(e, 'error')
    else:
        create_user(username, full_name, email, password, role)
        flash(f'Użytkownik {full_name} został dodany.', 'success')

    return redirect(url_for('users.list_users'))


@bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash('Użytkownik nie istnieje.', 'error')
        return redirect(url_for('users.list_users'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'cashier')
        is_active = int(request.form.get('is_active', 1))

        if not full_name:
            flash('Imię i nazwisko jest wymagane.', 'error')
            return render_template('settings/user_edit.html',
                                   active_tab='users', user=user)

        update_user(user_id, full_name, email, role, is_active)
        flash('Dane użytkownika zostały zaktualizowane.', 'success')
        return redirect(url_for('users.list_users'))

    return render_template('settings/user_edit.html', active_tab='users', user=user)


@bp.route('/<int:user_id>/password', methods=['POST'])
def change_password_view(user_id):
    new_password = request.form.get('new_password', '')
    new_password2 = request.form.get('new_password2', '')

    if not new_password:
        flash('Nowe hasło nie może być puste.', 'error')
    elif new_password != new_password2:
        flash('Hasła nie są identyczne.', 'error')
    else:
        change_password(user_id, new_password)
        flash('Hasło zostało zmienione.', 'success')

    return redirect(url_for('users.list_users'))


@bp.route('/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        new_status = 0 if user['is_active'] else 1
        update_user(user_id, user['full_name'], user['email'],
                    user['role'], new_status)
        label = 'aktywowany' if new_status else 'dezaktywowany'
        flash(f'Użytkownik {user["full_name"]} został {label}.', 'success')
    return redirect(url_for('users.list_users'))


@bp.route('/<int:user_id>/delete', methods=['POST'])
def delete_user_view(user_id):
    user = get_user_by_id(user_id)
    if user:
        delete_user(user_id)
        flash(f'Użytkownik {user["full_name"]} został usunięty.', 'success')
    return redirect(url_for('users.list_users'))
