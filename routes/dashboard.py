import calendar
import json
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, request

from models.expense import get_daily_totals, get_monthly_kpi, get_unpaid_expenses
from models.income import (get_income_daily_totals, get_monthly_income_kpi,
                            get_unpaid_incomes)

bp = Blueprint('dashboard', __name__)

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
    today = date.today()
    month = request.args.get('month', '').strip() or today.strftime('%Y-%m')
    try:
        year, mon = (int(p) for p in month.split('-'))
        date(year, mon, 1)
    except (ValueError, TypeError):
        month = today.strftime('%Y-%m')
        year, mon = today.year, today.month

    expense_kpi = get_monthly_kpi(month)
    income_kpi  = get_monthly_income_kpi(month)
    balance = float(income_kpi['total_gross'] or 0) - float(expense_kpi['total_gross'] or 0)
    net_balance = float(income_kpi['total_net'] or 0) - float(expense_kpi['total_net'] or 0)
    vat_balance = float(income_kpi['total_vat'] or 0) - float(expense_kpi['total_vat'] or 0)

    days_in_month = calendar.monthrange(year, mon)[1]

    exp_map  = {int(r['day']): float(r['total']) for r in get_daily_totals(month)}
    inc_map  = {int(r['day']): float(r['total']) for r in get_income_daily_totals(month)}
    expense_chart = json.dumps([exp_map.get(d, 0) for d in range(1, days_in_month + 1)])
    income_chart  = json.dumps([inc_map.get(d, 0) for d in range(1, days_in_month + 1)])

    unpaid_expenses = get_unpaid_expenses(20)
    unpaid_incomes  = get_unpaid_incomes(20)

    unpaid_expense_total = sum(float(e['amount_gross'] or 0) for e in unpaid_expenses)
    unpaid_income_total  = sum(float(i['amount_gross'] or 0) for i in unpaid_incomes)

    return render_template('dashboard.html',
        month=month,
        month_label=f"{MONTHS_PL[mon]} {year}",
        months=_last_months(),
        today=today,
        expense_kpi=expense_kpi,
        income_kpi=income_kpi,
        balance=balance,
        net_balance=net_balance,
        vat_balance=vat_balance,
        expense_chart=expense_chart,
        income_chart=income_chart,
        unpaid_expenses=unpaid_expenses,
        unpaid_incomes=unpaid_incomes,
        unpaid_expense_total=unpaid_expense_total,
        unpaid_income_total=unpaid_income_total,
        today_date=today,
    )
