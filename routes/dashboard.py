import calendar
import json
from datetime import date

from flask import Blueprint, render_template

from models.expense import get_daily_totals, get_monthly_kpi

bp = Blueprint('dashboard', __name__)

MONTHS_PL = {
    1: 'styczeń', 2: 'luty', 3: 'marzec', 4: 'kwiecień',
    5: 'maj', 6: 'czerwiec', 7: 'lipiec', 8: 'sierpień',
    9: 'wrzesień', 10: 'październik', 11: 'listopad', 12: 'grudzień',
}


@bp.route('/')
def index():
    today = date.today()
    month = today.strftime('%Y-%m')
    kpi = get_monthly_kpi(month)
    daily = get_daily_totals(month)

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    daily_map = {int(r['day']): float(r['total']) for r in daily}
    chart_data = [daily_map.get(d, 0) for d in range(1, days_in_month + 1)]

    return render_template('dashboard.html',
        month_label=f"{MONTHS_PL[today.month]} {today.year}",
        kpi=kpi,
        chart_data=json.dumps(chart_data),
        today=today,
    )
