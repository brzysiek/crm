import calendar
import json
from datetime import date

from flask import Blueprint, render_template

from models.expense import get_daily_totals, get_monthly_kpi, get_unpaid_expenses
from models.income import (get_income_daily_totals, get_monthly_income_kpi,
                            get_unpaid_incomes)

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

    expense_kpi = get_monthly_kpi(month)
    income_kpi  = get_monthly_income_kpi(month)
    balance = float(income_kpi['total_gross'] or 0) - float(expense_kpi['total_gross'] or 0)

    days_in_month = calendar.monthrange(today.year, today.month)[1]

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
        month_label=f"{MONTHS_PL[today.month]} {today.year}",
        today=today,
        expense_kpi=expense_kpi,
        income_kpi=income_kpi,
        balance=balance,
        expense_chart=expense_chart,
        income_chart=income_chart,
        unpaid_expenses=unpaid_expenses,
        unpaid_incomes=unpaid_incomes,
        unpaid_expense_total=unpaid_expense_total,
        unpaid_income_total=unpaid_income_total,
        today_date=today,
    )
