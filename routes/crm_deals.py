from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.crm_company import get_company_by_id
from models.crm_contact import get_contact_by_id
from models.crm_deal import (KANBAN_DEFAULT_HIDDEN_STAGES, STAGE_BADGE_CLASSES, STAGE_LABELS,
                              create_deal, delete_deal, get_all_deals, get_deal_by_id, update_deal)
from models.crm_deal_payment import (add_payment, delete_payment, get_payments_for_deal,
                                      maybe_auto_schedule_payment)
from models.crm_notes import (HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note,
                                get_history, get_notes)
from models.user import get_active_users

bp = Blueprint('crm_deals', __name__, url_prefix='/crm/deals')


def _parse_form(form):
    try:
        amount = float(form.get('amount') or 0) or None
    except ValueError:
        amount = None
    return {
        'name': form.get('name', '').strip(),
        'description': form.get('description', '').strip(),
        'amount': amount,
        'company_id': form.get('company_id', type=int),
        'contact_id': form.get('contact_id', type=int),
        'stage': form.get('stage', 'new'),
        'start_date': form.get('start_date', '').strip() or None,
        'end_date': form.get('end_date', '').strip() or None,
        'owner_user_id': form.get('owner_user_id', type=int),
    }


def _validate(data):
    errors = []
    if not data.get('name'):
        errors.append('Nazwa deala jest wymagana.')
    return errors


@bp.route('/')
def list_deals():
    sort = request.args.get('sort', 'created_at')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')
    stage = request.args.get('stage', '')

    deals = get_all_deals(sort=sort, direction=direction, search=search or None, stage=stage or None)
    return render_template('crm/deals/list.html',
        active_tab='deals', deals=deals, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
        sort=sort, direction=direction, filters={'search': search, 'stage': stage},
        kanban_default_hidden_stages=KANBAN_DEFAULT_HIDDEN_STAGES,
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_deal():
    owners = get_active_users()
    company_id = request.args.get('company_id', type=int)
    contact_id = request.args.get('contact_id', type=int)
    prefill_contact = get_contact_by_id(contact_id) if contact_id else None
    if not company_id and prefill_contact and prefill_contact.get('company_id'):
        company_id = prefill_contact['company_id']
    prefill_company = get_company_by_id(company_id) if company_id else None

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/deals/form.html',
                active_tab='deals', deal=request.form, owners=owners, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
                prefill_company=None, prefill_contact=None,
                action=url_for('crm_deals.new_deal'), title='Nowy deal')

        deal_id = create_deal(data, session.get('user_id'))
        maybe_auto_schedule_payment(deal_id, data.get('end_date'), data.get('amount'))
        flash('Deal został zapisany.', 'success')
        return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))

    deal = {}
    if company_id:
        deal['company_id'] = company_id
    if contact_id:
        deal['contact_id'] = contact_id
    return render_template('crm/deals/form.html',
        active_tab='deals', deal=deal, owners=owners, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
        prefill_company=prefill_company, prefill_contact=prefill_contact,
        action=url_for('crm_deals.new_deal'), title='Nowy deal')


@bp.route('/<int:deal_id>/edit', methods=['GET', 'POST'])
def edit_deal(deal_id):
    deal = get_deal_by_id(deal_id)
    if not deal:
        flash('Deal nie istnieje.', 'error')
        return redirect(url_for('crm_deals.list_deals'))

    owners = get_active_users()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/deals/form.html',
                active_tab='deals', deal=request.form, owners=owners, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
                prefill_company=None, prefill_contact=None,
                action=url_for('crm_deals.edit_deal', deal_id=deal_id), title='Edytuj deal')

        update_deal(deal_id, data, session.get('user_id'))
        maybe_auto_schedule_payment(deal_id, data.get('end_date'), data.get('amount'))
        flash('Deal został zaktualizowany.', 'success')
        return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))

    prefill_company = get_company_by_id(deal['company_id']) if deal.get('company_id') else None
    prefill_contact = get_contact_by_id(deal['contact_id']) if deal.get('contact_id') else None
    return render_template('crm/deals/form.html',
        active_tab='deals', deal=deal, owners=owners, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
        prefill_company=prefill_company, prefill_contact=prefill_contact,
        action=url_for('crm_deals.edit_deal', deal_id=deal_id), title='Edytuj deal')


@bp.route('/<int:deal_id>')
def view_deal(deal_id):
    deal = get_deal_by_id(deal_id)
    if not deal:
        flash('Deal nie istnieje.', 'error')
        return redirect(url_for('crm_deals.list_deals'))

    notes = get_notes('deal', deal_id)
    for n in notes:
        n['delete_url'] = url_for('crm_deals.delete_note_view', deal_id=deal_id, note_id=n['id'])

    payments = get_payments_for_deal(deal_id)

    return render_template('crm/deals/detail.html',
        active_tab='deals', deal=deal, stage_labels=STAGE_LABELS, stage_badge_classes=STAGE_BADGE_CLASSES,
        notes=notes,
        history=get_history('deal', deal_id),
        add_note_url=url_for('crm_deals.add_note_view', deal_id=deal_id),
        payments=payments,
        payments_total=sum(float(p['amount_net']) for p in payments),
        entity_type='deal', entity_id=deal_id,
        note_type_labels=NOTE_TYPE_LABELS,
        history_badge_labels=HISTORY_BADGE_LABELS,
    )


@bp.route('/<int:deal_id>/delete', methods=['POST'])
def delete_deal_view(deal_id):
    delete_deal(deal_id, session.get('user_id'))
    flash('Deal został usunięty.', 'success')
    return redirect(url_for('crm_deals.list_deals'))


@bp.route('/<int:deal_id>/notes', methods=['POST'])
def add_note_view(deal_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('deal', deal_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(deal_id, note_id):
    delete_note(note_id)
    return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/payments', methods=['POST'])
def add_payment_view(deal_id):
    month_value = request.form.get('pay_month', '').strip()
    try:
        amount = float((request.form.get('amount_net', '') or '').replace(',', '.'))
    except ValueError:
        amount = None
    if month_value and amount and amount > 0:
        add_payment(deal_id, f"{month_value}-01", amount)
        flash('Płatność została dodana.', 'success')
    else:
        flash('Podaj miesiąc i kwotę większą od zera.', 'error')
    return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/payments/<int:payment_id>/delete', methods=['POST'])
def delete_payment_view(deal_id, payment_id):
    delete_payment(payment_id)
    flash('Płatność została usunięta.', 'success')
    return redirect(url_for('crm_deals.view_deal', deal_id=deal_id))
