from datetime import date

from dateutil.relativedelta import relativedelta
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

bp = Blueprint('imports', __name__, url_prefix='/importy')

MONTHS_PL = {
    1: 'styczeń', 2: 'luty', 3: 'marzec', 4: 'kwiecień',
    5: 'maj', 6: 'czerwiec', 7: 'lipiec', 8: 'sierpień',
    9: 'wrzesień', 10: 'październik', 11: 'listopad', 12: 'grudzień',
}


def _last_months(n=18):
    months = []
    today = date.today()
    for i in range(n):
        d = today - relativedelta(months=i)
        months.append({
            'value': d.strftime('%Y-%m'),
            'label': f"{MONTHS_PL[d.month]} {d.year}",
        })
    return months


@bp.route('/')
def index():
    return redirect(url_for('imports.bank'))


# ── Bank ─────────────────────────────────────────────────────────────────────

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
    return render_template('imports/bank.html',
        active_tab='bank',
        pending_transactions=pending,
        bank_filter=bank_filter,
        type_filter=type_filter,
        import_log=import_log,
    )


@bp.route('/bank/import', methods=['POST'])
def bank_import():
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
    return redirect(url_for('imports.bank') + '#pending')


# ── Fakturownia ───────────────────────────────────────────────────────────────

@bp.route('/fakturownia', methods=['GET'])
def fakturownia():
    from models.invoice import get_pending_invoices, get_sync_log
    from models.settings import get_all_settings
    type_filter = request.args.get('type_filter', '')
    cfg = get_all_settings()
    pending  = get_pending_invoices(invoice_type=type_filter or None)
    sync_log = get_sync_log(10)
    return render_template('imports/fakturownia.html',
        active_tab='fakturownia',
        cfg=cfg,
        pending_invoices=pending,
        type_filter=type_filter,
        sync_log=sync_log,
        months=_last_months(),
    )


@bp.route('/fakturownia/invoices/<int:inv_id>/reject', methods=['POST'])
def reject_invoice_view(inv_id):
    from models.invoice import reject_invoice
    reject_invoice(inv_id)
    flash('Faktura została odrzucona.', 'success')
    return redirect(url_for('imports.fakturownia') + '#pending')


# ── Google Drive ──────────────────────────────────────────────────────────────

@bp.route('/gdrive', methods=['GET'])
def gdrive():
    from models.gdrive_invoice import get_pending_gdrive_invoices
    from models.settings import get_all_settings
    type_filter = request.args.get('type_filter', '')
    cfg = get_all_settings()
    pending = get_pending_gdrive_invoices(invoice_type=type_filter or None)
    return render_template('imports/gdrive.html',
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
    return redirect(url_for('imports.gdrive') + '#pending')
