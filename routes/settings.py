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


@bp.route('/logs')
def logs():
    return render_template('settings/logs.html', active_tab='logs')


@bp.route('/dictionary', methods=['GET'])
def dictionary():
    from models.dictionary import get_dict_items
    return render_template('settings/dictionary.html',
        active_tab='dictionary',
        expense_categories=get_dict_items('expense_category'),
        income_categories=get_dict_items('income_category'),
        vat_rates=get_dict_items('vat_rate'),
        payment_methods=get_dict_items('payment_method'),
    )


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
    return redirect(url_for('settings.dictionary'))


@bp.route('/dictionary/<int:item_id>/delete', methods=['POST'])
def dictionary_delete(item_id):
    from models.dictionary import delete_dict_item
    delete_dict_item(item_id)
    return redirect(url_for('settings.dictionary'))

