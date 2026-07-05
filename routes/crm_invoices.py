from flask import Blueprint, render_template, request

from models.invoice import get_all_invoices

bp = Blueprint('crm_invoices', __name__, url_prefix='/crm/invoices')


@bp.route('/')
def list_invoices():
    sort = request.args.get('sort', 'issue_date')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')
    status = request.args.get('status', '')

    invoices = get_all_invoices(invoice_type='income', search=search or None,
                                 status=status or None, sort=sort, direction=direction)
    return render_template('crm/invoices/list.html',
        active_tab='invoices', invoices=invoices,
        sort=sort, direction=direction, filters={'search': search, 'status': status},
    )
