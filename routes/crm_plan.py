import json
from datetime import date

from flask import Blueprint, render_template, request, session

from models.crm_deal_payment import get_payments_in_range
from models.user_settings import get_user_setting, set_user_setting

bp = Blueprint('crm_plan', __name__, url_prefix='/crm/plan')

MONTHS_PL_SHORT = {
    1: 'Sty', 2: 'Lut', 3: 'Mar', 4: 'Kwi', 5: 'Maj', 6: 'Cze',
    7: 'Lip', 8: 'Sie', 9: 'Wrz', 10: 'Paź', 11: 'Lis', 12: 'Gru',
}

DEFAULT_FORWARD = 2     # domyślnie: bieżący miesiąc + 2 miesiące naprzód
MAX_MONTHS = 24          # zabezpieczenie przed zbyt szerokim zakresem
SETTING_KEY = 'crm_plan_range'


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _parse_month(value: str):
    try:
        y, m = value.split('-')
        return int(y), int(m)
    except (ValueError, AttributeError):
        return None


def _months_word(n: int) -> str:
    if n == 1:
        return 'miesiąc'
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 'miesiące'
    return 'miesięcy'


@bp.route('/')
def index():
    today = date.today()
    default_start = _month_key(today.year, today.month)
    dy, dm = _shift_month(today.year, today.month, DEFAULT_FORWARD)
    default_end = _month_key(dy, dm)

    start_raw = request.args.get('start', '').strip()
    end_raw = request.args.get('end', '').strip()

    if start_raw or end_raw:
        start_raw = start_raw or default_start
        end_raw = end_raw or default_end
        set_user_setting(session['user_id'], SETTING_KEY,
                          json.dumps({'start': start_raw, 'end': end_raw}))
    else:
        saved = get_user_setting(session['user_id'], SETTING_KEY)
        start_raw, end_raw = default_start, default_end
        if saved:
            try:
                data = json.loads(saved)
                start_raw = data.get('start', default_start)
                end_raw = data.get('end', default_end)
            except (ValueError, TypeError):
                pass

    start = _parse_month(start_raw) or _parse_month(default_start)
    end = _parse_month(end_raw) or _parse_month(default_end)

    start_idx = start[0] * 12 + (start[1] - 1)
    end_idx = end[0] * 12 + (end[1] - 1)
    if end_idx < start_idx:
        start_idx, end_idx = end_idx, start_idx
    if end_idx - start_idx + 1 > MAX_MONTHS:
        end_idx = start_idx + MAX_MONTHS - 1

    months = []
    for idx in range(start_idx, end_idx + 1):
        y, m = idx // 12, idx % 12 + 1
        months.append({
            'year': y, 'month': m, 'key': _month_key(y, m),
            'label_short': f"{MONTHS_PL_SHORT[m]} {y}",
            'is_current': (y, m) == (today.year, today.month),
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
    current_index = next((i for i, m in enumerate(months) if m['is_current']), -1)

    return render_template('crm/plan/index.html',
        active_tab='plan', months=months,
        chart_labels=chart_labels, chart_data=chart_data, current_index=current_index,
        grand_total=sum(m['total'] for m in months),
        range_start=months[0]['key'], range_end=months[-1]['key'],
        default_start=default_start, default_end=default_end,
        months_word=_months_word(len(months)),
    )
