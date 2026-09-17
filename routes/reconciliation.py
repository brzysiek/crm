from flask import Blueprint, jsonify, render_template, request

import models.reconciliation as reconciliation

bp = Blueprint('reconciliation', __name__, url_prefix='/finanse/uzgadnianie')


def _jsonify_row(row: dict) -> dict:
    row = dict(row)
    for k in ('date', 'created_at', 'imported_at', 'payment_due_date'):
        if row.get(k) is not None:
            row[k] = str(row[k])
    return row


@bp.route('/')
def index():
    expense_txns = [_jsonify_row(r) for r in reconciliation.get_unmatched_bank_transactions('expense')]
    income_txns = [_jsonify_row(r) for r in reconciliation.get_unmatched_bank_transactions('income')]
    expense_records = [_jsonify_row(r) for r in reconciliation.get_unmatched_expense_records()]
    income_records = [_jsonify_row(r) for r in reconciliation.get_unmatched_income_records()]
    return render_template('reconciliation/index.html',
        active_tab='uzgadnianie',
        expense_txns=expense_txns,
        income_txns=income_txns,
        expense_records=expense_records,
        income_records=income_records,
        summary=reconciliation.summary(),
    )


@bp.route('/api/candidates-for-transaction/<int:txn_id>')
def api_candidates_for_transaction(txn_id):
    results = reconciliation.get_candidates_for_transaction(txn_id)
    out = []
    for r in results:
        out.append({
            'record_type': r['record_type'],
            'score': r['score'],
            'remaining': r['remaining'],
            'record': _jsonify_row(r['record']),
        })
    return jsonify(out)


@bp.route('/api/candidates-for-record')
def api_candidates_for_record():
    record_type = request.args.get('record_type')
    record_id = request.args.get('record_id', type=int)
    if record_type not in ('expense', 'income') or not record_id:
        return jsonify({'error': 'Nieprawidłowe parametry.'}), 400
    results = reconciliation.get_candidates_for_record(record_type, record_id)
    out = []
    for r in results:
        out.append({
            'score': r['score'],
            'transaction': _jsonify_row(r['transaction']),
        })
    return jsonify(out)


@bp.route('/api/link', methods=['POST'])
def api_link():
    data = request.get_json(silent=True) or {}
    record_type = data.get('record_type')
    record_id = data.get('record_id')
    bank_txn_id = data.get('bank_txn_id')
    if record_type not in ('expense', 'income') or not record_id or not bank_txn_id:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowe parametry.'}), 400
    result = reconciliation.link(record_type, int(record_id), int(bank_txn_id))
    return jsonify({'status': 'ok', **result})


@bp.route('/api/unlink', methods=['POST'])
def api_unlink():
    data = request.get_json(silent=True) or {}
    record_type = data.get('record_type')
    record_id = data.get('record_id')
    bank_txn_id = data.get('bank_txn_id')
    if record_type not in ('expense', 'income') or not record_id or not bank_txn_id:
        return jsonify({'status': 'error', 'message': 'Nieprawidłowe parametry.'}), 400
    result = reconciliation.unlink(record_type, int(record_id), int(bank_txn_id))
    return jsonify({'status': 'ok', **result})


@bp.route('/api/summary')
def api_summary():
    return jsonify(reconciliation.summary())
