"""Ustawienia aplikacji.

Zakres celowo wąski: konto, wygląd, integracje z usługami zewnętrznymi, słowniki
podpowiedzi, użytkownicy i dziennik zdarzeń. Rzeczy, które edytuje się w trakcie
pracy — listy kontaktów, konteksty GTD, stopki kampanii — mieszkają przy swoich
widokach (crm_contacts, gtd, email_campaigns), bo tam się ich szuka.
"""

from flask import (Blueprint, flash, redirect,
                   render_template, request, session, url_for)

from models.settings import get_all_settings

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/')
def index():
    return redirect(url_for('settings.account'))


@bp.route('/konto', methods=['GET', 'POST'])
def account():
    from models.user import (change_password, get_user_avatar, get_user_by_id,
                              get_user_by_username, update_user_profile)

    if request.method == 'POST':
        if request.form.get('form') == 'avatar':
            _save_avatar(session['user_id'])
        elif request.form.get('form') == 'profile':
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()

            errors = []
            if not username:
                errors.append('Login nie może być pusty.')
            if not full_name:
                errors.append('Imię i nazwisko nie może być puste.')
            if not errors:
                existing = get_user_by_username(username)
                if existing and existing['id'] != session['user_id']:
                    errors.append(f'Login „{username}" jest już zajęty.')

            if errors:
                for e in errors:
                    flash(e, 'error')
            else:
                update_user_profile(session['user_id'], username, full_name, email)
                session['username'] = username
                session['full_name'] = full_name
                flash('Dane konta zostały zaktualizowane.', 'success')
        elif request.form.get('form') == 'security':
            from models.settings import set_setting
            set_setting('login_2fa', 'on' if request.form.get('login_2fa') else 'off')
            flash('Ustawienia logowania zostały zapisane.', 'success')
        else:
            new_password = request.form.get('new_password', '')
            new_password2 = request.form.get('new_password2', '')

            if not new_password:
                flash('Nowe hasło nie może być puste.', 'error')
            elif new_password != new_password2:
                flash('Hasła nie są identyczne.', 'error')
            else:
                change_password(session['user_id'], new_password)
                flash('Hasło zostało zmienione.', 'success')
        return redirect(url_for('settings.account'))

    from models.settings import get_setting
    from services.mailer import is_configured

    user = get_user_by_id(session['user_id'])
    return render_template('settings/account.html', active_tab='account', user=user,
        has_avatar=bool(get_user_avatar(session['user_id'])),
        login_2fa=get_setting('login_2fa', 'on') != 'off', mail_configured=is_configured())


# ── Zdjęcie użytkownika ──────────────────────────────────────────────────────
# Zdjęcie trzymamy w bazie jako data URI (tak samo jak logo aplikacji), ale do
# przeglądarki idzie osobnym adresem, a nie w treści strony: ikonka jest na
# każdym ekranie, więc wklejanie kilkunastu kB base64 do każdego HTML-a byłoby
# marnotrawstwem. Osobny adres można zacache'ować.

_ALLOWED_AVATAR_MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
_MAX_AVATAR_UPLOAD_BYTES = 8_000_000


def _save_avatar(user_id: int) -> None:
    """Zapisuje albo kasuje zdjęcie zalogowanego użytkownika. Wejściowy plik
    może być dowolnie duży (zdjęcie z telefonu) — do bazy trafia dopiero
    kwadratowa miniatura JPEG, więc limit na wejściu chroni tylko pamięć
    procesu, a nie rozmiar kolumny."""
    import base64
    from models.user import set_user_avatar
    from services.images import build_avatar

    if request.form.get('remove_avatar') == '1':
        set_user_avatar(user_id, None)
        flash('Zdjęcie zostało usunięte.', 'success')
        return

    f = request.files.get('avatar')
    if not f or not f.filename:
        flash('Nie wybrano pliku ze zdjęciem.', 'error')
        return
    if f.mimetype not in _ALLOWED_AVATAR_MIMES:
        flash(f'Nieobsługiwany format pliku ({f.filename}). Wybierz JPG, PNG, WEBP lub GIF.', 'error')
        return
    content = f.read()
    if len(content) > _MAX_AVATAR_UPLOAD_BYTES:
        flash('Plik jest za duży, maks. 8 MB.', 'error')
        return
    try:
        thumb = build_avatar(content)
    except ValueError as e:
        flash(str(e), 'error')
        return
    set_user_avatar(user_id, 'data:image/jpeg;base64,' + base64.b64encode(thumb).decode('ascii'))
    flash('Zdjęcie zostało zapisane.', 'success')


@bp.route('/zdjecie/<int:user_id>')
def avatar(user_id: int):
    import base64
    from flask import Response
    from models.user import get_user_avatar

    data_uri = get_user_avatar(user_id) or ''
    if not data_uri.startswith('data:image/jpeg;base64,'):
        return '', 404
    try:
        img_bytes = base64.b64decode(data_uri.split(',', 1)[1])
    except Exception:
        return '', 404
    resp = Response(img_bytes, mimetype='image/jpeg')
    # Adres niesie znacznik zmiany (?v=...), więc treść pod danym adresem jest
    # niezmienna i może leżeć w cache przeglądarki dłużej niż godzinę.
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


# ── Integracje ───────────────────────────────────────────────────────────────
# Jedna strona, cztery karty (Fakturownia, Google, e-mail, Gemini). Każda karta
# zapisuje się osobno — `form_section` mówi, których kluczy dotyczy POST, więc
# zapis jednej integracji nie czyści pól sąsiedniej.

@bp.route('/integracje', methods=['GET', 'POST'])
def general():
    from models.settings import get_all_settings, set_many
    if request.method == 'POST':
        section = request.form.get('form_section', 'all')
        data = {}
        if section in ('fakturownia', 'all'):
            data['fakturownia_subdomain']     = request.form.get('subdomain', '').strip()
            data['fakturownia_api_key']       = request.form.get('api_key', '').strip()
            data['fakturownia_sync_schedule'] = request.form.get('sync_schedule', 'manual')
        if section in ('gdrive', 'all'):
            data['google_drive_folder_id'] = request.form.get('google_drive_folder_id', '').strip()
            data['google_drive_crm_folder_id'] = request.form.get('google_drive_crm_folder_id', '').strip()
            data['gtd_gcal_calendar_id'] = request.form.get('gtd_gcal_calendar_id', '').strip()
            data['gtd_gcal_read_calendar_id'] = request.form.get('gtd_gcal_read_calendar_id', '').strip()
            drive_token = request.form.get('google_drive_api_token', '').strip()
            if drive_token:
                data['google_drive_api_token'] = drive_token
        if section in ('email', 'all'):
            data['gmail_sender_email'] = request.form.get('gmail_sender_email', '').strip()
            data['gmail_sender_name'] = request.form.get('gmail_sender_name', '').strip()
            data['email_daily_limit'] = request.form.get('email_daily_limit', '150').strip() or '150'
            data['email_batch_per_run'] = request.form.get('email_batch_per_run', '3').strip() or '3'
            data['crm_vcard_email_on_create'] = '1' if request.form.get('crm_vcard_email_on_create') == '1' else '0'
            data['crm_vcard_email_on_edit'] = '1' if request.form.get('crm_vcard_email_on_edit') == '1' else '0'
        if section in ('gemini', 'all'):
            data['gemini_model'] = request.form.get('gemini_model', 'gemini-2.5-flash').strip()
            gemini_key = request.form.get('gemini_api_key', '').strip()
            if gemini_key:
                data['gemini_api_key'] = gemini_key
        set_many(data)
        flash('Konfiguracja została zapisana.', 'success')
        return redirect(url_for('settings.general'))
    cfg = get_all_settings()
    return render_template('settings/general.html', active_tab='general', cfg=cfg)


_ALLOWED_LOGO_MIMES = {
    'image/png', 'image/jpeg', 'image/svg+xml', 'image/webp',
    'image/x-icon', 'image/vnd.microsoft.icon',
}
_MAX_LOGO_BYTES = 1_500_000


@bp.route('/aplikacja', methods=['GET', 'POST'])
def appearance():
    import base64
    from models.settings import get_all_settings, set_many

    if request.method == 'POST':
        data = {}

        name = request.form.get('app_name', '').strip()
        if name:
            data['app_name'] = name
        else:
            flash('Nazwa aplikacji nie może być pusta.', 'error')

        for field in ('logo_main', 'logo_thumb'):
            if request.form.get(f'remove_{field}') == '1':
                data[field] = ''
                continue
            f = request.files.get(field)
            if f and f.filename:
                if f.mimetype not in _ALLOWED_LOGO_MIMES:
                    flash(f'Nieobsługiwany format pliku ({f.filename}).', 'error')
                    continue
                img_bytes = f.read()
                if len(img_bytes) > _MAX_LOGO_BYTES:
                    flash(f'Plik jest za duży ({f.filename}), maks. 1.5 MB.', 'error')
                    continue
                encoded = base64.b64encode(img_bytes).decode('ascii')
                data[field] = f'data:{f.mimetype};base64,{encoded}'

        if data:
            set_many(data)
            flash('Ustawienia aplikacji zostały zapisane.', 'success')
        return redirect(url_for('settings.appearance'))

    cfg = get_all_settings()
    return render_template('settings/appearance.html', active_tab='appearance', cfg=cfg)


@bp.route('/dziennik')
def logs():
    return render_template('settings/logs.html', active_tab='logs')


# ── Słowniki ─────────────────────────────────────────────────────────────────
# Wszystkie listy podpowiedzi w jednym miejscu, pogrupowane po module, którego
# dotyczą. Wcześniej te same treści siedziały pod czterema pozycjami menu
# („Finanse", „CRM", „Słownik", „Konteksty") i nie dało się zgadnąć, gdzie czego
# szukać. Konteksty GTD pokazujemy tu tylko poglądowo — edytuje się je przy
# zadaniach, więc nie ma dwóch edytorów tej samej rzeczy.

@bp.route('/slowniki')
def dictionaries():
    from models.crm_tags import get_tags
    from models.dictionary import get_dict_items
    from models.gtd_context import get_all_contexts
    return render_template('settings/dictionaries.html',
        active_tab='dictionaries',
        tags=get_tags('tag', with_counts=True),
        industries=get_tags('industry', with_counts=True),
        sources=get_tags('source', with_counts=True),
        expense_categories=get_dict_items('expense_category'),
        income_categories=get_dict_items('income_category'),
        vat_rates=get_dict_items('vat_rate'),
        payment_methods=get_dict_items('payment_method'),
        contexts=get_all_contexts(),
    )


def _back_to_dictionaries(anchor):
    return redirect(url_for('settings.dictionaries') + ('#' + anchor if anchor else ''))


@bp.route('/slowniki/pozycja/dodaj', methods=['POST'])
def dictionary_add():
    from models.dictionary import add_dict_item
    dict_type = request.form.get('dict_type', '').strip()
    value     = request.form.get('value', '').strip()
    label     = request.form.get('label', '').strip() or None
    if dict_type and value:
        try:
            add_dict_item(dict_type, value, label)
        except Exception:
            flash('Taka pozycja już istnieje.', 'error')
    return _back_to_dictionaries(request.form.get('anchor', '').strip())


@bp.route('/slowniki/pozycja/<int:item_id>/usun', methods=['POST'])
def dictionary_delete(item_id):
    from models.dictionary import delete_dict_item
    delete_dict_item(item_id)
    return _back_to_dictionaries(request.form.get('anchor', '').strip())


@bp.route('/slowniki/tag/dodaj', methods=['POST'])
def tag_add():
    from models.crm_tags import add_tag
    kind = request.form.get('kind', '').strip()
    name = request.form.get('name', '').strip()
    if kind in ('tag', 'industry', 'source') and name:
        try:
            add_tag(kind, name)
        except Exception:
            flash('Taka pozycja już istnieje.', 'error')
    return _back_to_dictionaries(request.form.get('anchor', '').strip())


@bp.route('/slowniki/tag/<int:tag_id>/nazwa', methods=['POST'])
def tag_rename(tag_id):
    """Zmiana nazwy zamiast „usuń i dodaj od nowa" — powiązania idą po tag_id,
    więc poprawka literówki nie odpina wartości od firm i kontaktów."""
    from models.crm_tags import rename_tag
    try:
        rename_tag(tag_id, request.form.get('name', ''))
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        flash('Nie udało się zmienić nazwy.', 'error')
    return _back_to_dictionaries(request.form.get('anchor', '').strip())


@bp.route('/slowniki/tag/<int:tag_id>/usun', methods=['POST'])
def tag_delete(tag_id):
    from models.crm_tags import delete_tag
    delete_tag(tag_id)
    return _back_to_dictionaries(request.form.get('anchor', '').strip())
