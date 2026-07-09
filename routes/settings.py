from flask import (Blueprint, flash, redirect,
                   render_template, request, url_for)

from models.settings import get_all_settings

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/')
def index():
    return redirect(url_for('settings.general'))


@bp.route('/general', methods=['GET', 'POST'])
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
            drive_token = request.form.get('google_drive_api_token', '').strip()
            if drive_token:
                data['google_drive_api_token'] = drive_token
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


@bp.route('/appearance', methods=['GET', 'POST'])
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
            flash('Ustawienia wyglądu zostały zapisane.', 'success')
        return redirect(url_for('settings.appearance'))

    cfg = get_all_settings()
    return render_template('settings/appearance.html', active_tab='appearance', cfg=cfg)


@bp.route('/logs')
def logs():
    return render_template('settings/logs.html', active_tab='logs')


@bp.route('/finance', methods=['GET'])
def finance():
    from models.dictionary import get_dict_items
    return render_template('settings/finance.html',
        active_tab='finance',
        expense_categories=get_dict_items('expense_category'),
        income_categories=get_dict_items('income_category'),
    )


@bp.route('/dictionary', methods=['GET'])
def dictionary():
    from models.dictionary import get_dict_items
    return render_template('settings/dictionary.html',
        active_tab='dictionary',
        vat_rates=get_dict_items('vat_rate'),
        payment_methods=get_dict_items('payment_method'),
    )


_FINANCE_DICT_TYPES = ('expense_category', 'income_category')


@bp.route('/dictionary/add', methods=['POST'])
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
    target = 'settings.finance' if dict_type in _FINANCE_DICT_TYPES else 'settings.dictionary'
    return redirect(url_for(target))


@bp.route('/dictionary/<int:item_id>/delete', methods=['POST'])
def dictionary_delete(item_id):
    from models.dictionary import delete_dict_item, get_dict_item_type
    dict_type = get_dict_item_type(item_id)
    delete_dict_item(item_id)
    target = 'settings.finance' if dict_type in _FINANCE_DICT_TYPES else 'settings.dictionary'
    return redirect(url_for(target))


@bp.route('/crm', methods=['GET'])
def crm_settings():
    from models.crm_tags import get_tags
    return render_template('settings/crm.html',
        active_tab='crm',
        tags=get_tags('tag'),
        industries=get_tags('industry'),
        sources=get_tags('source'),
    )


@bp.route('/crm/add', methods=['POST'])
def crm_tag_add():
    from models.crm_tags import add_tag
    kind = request.form.get('kind', '').strip()
    name = request.form.get('name', '').strip()
    if kind in ('tag', 'industry', 'source') and name:
        try:
            add_tag(kind, name)
        except Exception:
            flash('Taka pozycja już istnieje.', 'error')
    return redirect(url_for('settings.crm_settings'))


@bp.route('/crm/<int:tag_id>/delete', methods=['POST'])
def crm_tag_delete(tag_id):
    from models.crm_tags import delete_tag
    delete_tag(tag_id)
    return redirect(url_for('settings.crm_settings'))

