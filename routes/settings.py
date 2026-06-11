from flask import (Blueprint, flash, jsonify, redirect,
                   render_template, request, url_for)

from models.invoice import (add_sync_log, get_pending_invoices,
                             get_sync_log, reject_invoice)
from models.settings import get_all_settings, set_many

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/')
def index():
    return redirect(url_for('settings.general'))


@bp.route('/general')
def general():
    return render_template('settings/general.html', active_tab='general')


@bp.route('/bank', methods=['GET', 'POST'])
def bank():
    from models.bank_transaction import (get_pending_bank_transactions,
                                          upsert_bank_transaction)
    from services.bank_import import parse_file

    bank_filter = request.args.get('bank_filter', '')
    type_filter = request.args.get('type_filter', '')

    if request.method == 'POST':
        bank_type = request.form.get('bank_type', '')
        uploaded  = request.files.get('csv_file')
        if not bank_type or not uploaded or not uploaded.filename:
            flash('Wybierz bank i wskaż plik CSV.', 'error')
        else:
            try:
                rows      = parse_file(bank_type, uploaded.read())
                new_count = sum(1 for r in rows if upsert_bank_transaction(r))
                flash(
                    f'Plik odczytano: {len(rows)} transakcji, '
                    f'nowych (do akceptacji): {new_count}.',
                    'success',
                )
            except Exception as exc:
                flash(f'Błąd importu: {exc}', 'error')
        return redirect(url_for('settings.bank'))

    pending = get_pending_bank_transactions(
        bank=bank_filter or None,
        txn_type=type_filter or None,
    )
    return render_template('settings/bank.html',
        active_tab='bank',
        pending_transactions=pending,
        bank_filter=bank_filter,
        type_filter=type_filter,
    )


@bp.route('/bank/transactions/<int:txn_id>/reject', methods=['POST'])
def reject_bank_txn_view(txn_id):
    from models.bank_transaction import reject_bank_transaction
    reject_bank_transaction(txn_id)
    flash('Transakcja odrzucona.', 'success')
    return redirect(url_for('settings.bank') + '#pending')


@bp.route('/fakturownia', methods=['GET', 'POST'])
def fakturownia():
    if request.method == 'POST':
        set_many({
            'fakturownia_subdomain':       request.form.get('subdomain', '').strip(),
            'fakturownia_api_key':         request.form.get('api_key', '').strip(),
            'fakturownia_sync_schedule':   request.form.get('sync_schedule', 'manual'),
            'fakturownia_filter_category': request.form.get('filter_category', 'expense'),
        })
        flash('Konfiguracja Fakturowni została zapisana.', 'success')
        return redirect(url_for('settings.fakturownia'))

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


