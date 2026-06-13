from flask import (Blueprint, flash, jsonify, redirect,
                   render_template, request, url_for)

from models.invoice import (add_sync_log, get_pending_invoices,
                             get_sync_log, reject_invoice)
from models.settings import get_all_settings

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/')
def index():
    return redirect(url_for('settings.general'))


@bp.route('/general', methods=['GET', 'POST'])
def general():
    from models.settings import get_all_settings, set_many
    if request.method == 'POST':
        data = {
            'fakturownia_subdomain':     request.form.get('subdomain', '').strip(),
            'fakturownia_api_key':       request.form.get('api_key', '').strip(),
            'fakturownia_sync_schedule': request.form.get('sync_schedule', 'manual'),
            'google_drive_folder_id':    request.form.get('google_drive_folder_id', '').strip(),
            'gemini_model':              request.form.get('gemini_model', 'gemini-2.5-flash').strip(),
        }
        # Only overwrite secret tokens when a new value is explicitly provided
        drive_token = request.form.get('google_drive_api_token', '').strip()
        if drive_token:
            data['google_drive_api_token'] = drive_token
        gemini_key = request.form.get('gemini_api_key', '').strip()
        if gemini_key:
            data['gemini_api_key'] = gemini_key
        set_many(data)
        flash('Konfiguracja została zapisana.', 'success')
        return redirect(url_for('settings.general'))
    cfg = get_all_settings()
    return render_template('settings/general.html', active_tab='general', cfg=cfg)


@bp.route('/bank', methods=['GET'])
def bank():
    from models.bank_transaction import (get_bank_import_log,
                                          get_pending_bank_transactions)
    bank_filter = request.args.get('bank_filter', '')
    type_filter = request.args.get('type_filter', '')
    pending = get_pending_bank_transactions(
        bank=bank_filter or None,
        txn_type=type_filter or None,
    )
    import_log = get_bank_import_log(15)
    return render_template('settings/bank.html',
        active_tab='bank',
        pending_transactions=pending,
        bank_filter=bank_filter,
        type_filter=type_filter,
        import_log=import_log,
    )


@bp.route('/bank/import', methods=['POST'])
def bank_import():
    """AJAX: przyjmuje multipart/form-data, zwraca JSON."""
    from models.bank_transaction import (add_bank_import_log,
                                          upsert_bank_transaction)
    from services.bank_import import parse_file

    bank_type = request.form.get('bank_type', '').strip()
    uploaded  = request.files.get('csv_file')

    if not bank_type or not uploaded or not uploaded.filename:
        return jsonify({'status': 'error', 'message': 'Wybierz bank i wskaż plik CSV.'})

    filename = uploaded.filename
    try:
        rows      = parse_file(bank_type, uploaded.read())
        new_count = sum(1 for r in rows if upsert_bank_transaction(r))
        add_bank_import_log(bank_type, filename, len(rows), new_count)
        return jsonify({
            'status':     'ok',
            'rows_found': len(rows),
            'rows_new':   new_count,
            'bank':       bank_type,
            'filename':   filename,
        })
    except Exception as exc:
        try:
            add_bank_import_log(bank_type, filename, 0, 0, 'error', str(exc))
        except Exception:
            pass
        return jsonify({'status': 'error', 'message': str(exc)})


@bp.route('/bank/transactions/<int:txn_id>/reject', methods=['POST'])
def reject_bank_txn_view(txn_id):
    from models.bank_transaction import reject_bank_transaction
    reject_bank_transaction(txn_id)
    flash('Transakcja odrzucona.', 'success')
    return redirect(url_for('settings.bank') + '#pending')


@bp.route('/fakturownia', methods=['GET'])
def fakturownia():
    type_filter = request.args.get('type_filter', '')
    cfg = get_all_settings()
    pending = get_pending_invoices(invoice_type=type_filter or None)
    sync_log = get_sync_log(10)
    return render_template('settings/fakturownia.html',
        active_tab='fakturownia',
        cfg=cfg,
        pending_invoices=pending,
        type_filter=type_filter,
        sync_log=sync_log,
    )


@bp.route('/fakturownia/invoices/<int:inv_id>/reject', methods=['POST'])
def reject_invoice_view(inv_id):
    reject_invoice(inv_id)
    flash('Faktura została odrzucona.', 'success')
    return redirect(url_for('settings.fakturownia') + '#pending')


@bp.route('/gdrive', methods=['GET'])
def gdrive():
    from models.gdrive_invoice import get_pending_gdrive_invoices
    type_filter = request.args.get('type_filter', '')
    cfg = get_all_settings()
    pending = get_pending_gdrive_invoices(invoice_type=type_filter or None)
    return render_template('settings/gdrive.html',
        active_tab='gdrive',
        cfg=cfg,
        pending_invoices=pending,
        type_filter=type_filter,
    )


@bp.route('/gdrive/invoices/<int:inv_id>/reject', methods=['POST'])
def reject_gdrive_invoice_view(inv_id):
    from models.gdrive_invoice import reject_gdrive_invoice
    reject_gdrive_invoice(inv_id)
    flash('Faktura została odrzucona.', 'success')
    return redirect(url_for('settings.gdrive') + '#pending')


@bp.route('/logs')
def logs():
    return render_template('settings/logs.html', active_tab='logs')

