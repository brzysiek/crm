from datetime import date

from flask import Blueprint, render_template

from models.crm_deal_payment import get_payments_in_range

bp = Blueprint('crm_plan', __name__, url_prefix='/crm/plan')

MONTHS_PL_SHORT = {
    1: 'Sty', 2: 'Lut', 3: 'Mar', 4: 'Kwi', 5: 'Maj', 6: 'Cze',
    7: 'Lip', 8: 'Sie', 9: 'Wrz', 10: 'Paź', 11: 'Lis', 12: 'Gru',
}

WINDOW_BACK = 3
WINDOW_FORWARD = 3


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


@bp.route('/')
def index():
    today = date.today()
    months = []
    for delta in range(-WINDOW_BACK, WINDOW_FORWARD + 1):
        y, m = _shift_month(today.year, today.month, delta)
        months.append({
            'year': y, 'month': m, 'key': f"{y:04d}-{m:02d}",
            'label_short': f"{MONTHS_PL_SHORT[m]} {y}",
            'is_current': delta == 0,
            'payments': [], 'total': 0.0,
        })

    start_key = months[0]['key'] + '-01'
    end_key = months[-1]['key'] + '-01'
    payments = get_payments_in_range(start_key, end_key)

    by_key = {m['key']: m for m in months}
    for p in payments:
        pay_month = p['pay_month']
        key = pay_month.strftime('%Y-%m') if hasattr(pay_month, 'strftime') else str(pay_month)[:7]
        bucket = by_key.get(key)
        if bucket is not None:
            bucket['payments'].append(p)
            bucket['total'] += float(p['amount_net'])

    chart_labels = [m['label_short'] for m in months]
    chart_data = [round(m['total'], 2) for m in months]
    current_index = WINDOW_BACK

    return render_template('crm/plan/index.html',
        active_tab='plan', months=months,
        chart_labels=chart_labels, chart_data=chart_data, current_index=current_index,
        grand_total=sum(m['total'] for m in months),
    )
