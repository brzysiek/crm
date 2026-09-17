from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.crm_notes import (HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note,
                                get_history, get_notes)
from models.mna_company import (create_mna_company, delete_mna_company, get_all_mna_companies,
                                  get_mna_company_by_id, search_mna_companies, set_starred,
                                  update_mna_company)
from models.mna_contact import get_all_mna_contacts
from models.mna_deal import get_deals_for_company

bp = Blueprint('mna_companies', __name__, url_prefix='/mna/firmy')


def _parse_form(form):
    return {
        'name': form.get('name', '').strip(),
        'short_name': form.get('short_name', '').strip(),
        'country': form.get('country', '').strip() or 'Polska',
        'city': form.get('city', '').strip(),
        'voivodeship': form.get('voivodeship', '').strip(),
        'street': form.get('street', '').strip(),
        'house_number': form.get('house_number', '').strip(),
        'flat_number': form.get('flat_number', '').strip(),
        'postal_code': form.get('postal_code', '').strip(),
        'email': form.get('email', '').strip(),
        'phone': form.get('phone', '').strip(),
        'nip': form.get('nip', '').strip(),
        'krs': form.get('krs', '').strip(),
        'website': form.get('website', '').strip(),
        'linkedin_url': form.get('linkedin_url', '').strip(),
        'description': form.get('description', '').strip(),
        'short_description': form.get('short_description', '').strip(),
    }


def _validate(data):
    errors = []
    if not data.get('name'):
        errors.append('Nazwa firmy jest wymagana.')
    return errors


@bp.route('/')
def list_companies():
    sort = request.args.get('sort', 'name')
    direction = request.args.get('dir', 'asc')
    search = request.args.get('search', '')
    companies = get_all_mna_companies(sort=sort, direction=direction, search=search or None)
    return render_template('mna_companies/list.html',
        active_tab='mna_companies', companies=companies, sort=sort, direction=direction,
        filters={'search': search})


@bp.route('/new', methods=['GET', 'POST'])
def new_company():
    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_companies/form.html',
                active_tab='mna_companies', company=request.form,
                action=url_for('mna_companies.new_company'), title='Nowa firma M&A')

        company_id = create_mna_company(data, session.get('user_id'))
        flash('Firma została zapisana.', 'success')
        return redirect(url_for('mna_companies.view_company', company_id=company_id))

    return render_template('mna_companies/form.html',
        active_tab='mna_companies', company={},
        action=url_for('mna_companies.new_company'), title='Nowa firma M&A')


@bp.route('/<int:company_id>/edit', methods=['GET', 'POST'])
def edit_company(company_id):
    company = get_mna_company_by_id(company_id)
    if not company:
        flash('Firma nie istnieje.', 'error')
        return redirect(url_for('mna_companies.list_companies'))

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_companies/form.html',
                active_tab='mna_companies', company=request.form,
                action=url_for('mna_companies.edit_company', company_id=company_id), title='Edytuj firmę M&A')

        update_mna_company(company_id, data, session.get('user_id'))
        flash('Firma została zaktualizowana.', 'success')
        return redirect(url_for('mna_companies.view_company', company_id=company_id))

    return render_template('mna_companies/form.html',
        active_tab='mna_companies', company=company,
        action=url_for('mna_companies.edit_company', company_id=company_id), title='Edytuj firmę M&A')


@bp.route('/<int:company_id>')
def view_company(company_id):
    company = get_mna_company_by_id(company_id)
    if not company:
        flash('Firma nie istnieje.', 'error')
        return redirect(url_for('mna_companies.list_companies'))

    contacts = get_all_mna_contacts(company_id=company_id)
    deal_targets = get_deals_for_company(company_id)

    notes = get_notes('mna_company', company_id)
    for n in notes:
        n['delete_url'] = url_for('mna_companies.delete_note_view', company_id=company_id, note_id=n['id'])
    history = get_history('mna_company', company_id)

    street_line = ' '.join(filter(None, [company.get('street'), company.get('house_number')]))
    if company.get('flat_number'):
        street_line += f" lok. {company['flat_number']}"
    address = ', '.join(filter(None, [
        street_line or None, company.get('postal_code'), company.get('city'), company.get('country'),
    ]))

    return render_template('mna_companies/detail.html',
        active_tab='mna_companies', company=company, address=address,
        contacts=contacts, deal_targets=deal_targets,
        notes=notes, history=history,
        add_note_url=url_for('mna_companies.add_note_view', company_id=company_id),
        entity_type='mna_company', entity_id=company_id,
        note_type_labels=NOTE_TYPE_LABELS, history_badge_labels=HISTORY_BADGE_LABELS,
    )


@bp.route('/<int:company_id>/toggle-star', methods=['POST'])
def toggle_star_view(company_id):
    company = get_mna_company_by_id(company_id)
    if company:
        set_starred(company_id, not company.get('is_starred'))
    return redirect(url_for('mna_companies.view_company', company_id=company_id))


@bp.route('/<int:company_id>/delete', methods=['POST'])
def delete_company_view(company_id):
    delete_mna_company(company_id, session.get('user_id'))
    flash('Firma została zarchiwizowana.', 'success')
    return redirect(url_for('mna_companies.list_companies'))


@bp.route('/<int:company_id>/notes', methods=['POST'])
def add_note_view(company_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('mna_company', company_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('mna_companies.view_company', company_id=company_id))


@bp.route('/<int:company_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(company_id, note_id):
    delete_note(note_id)
    return redirect(url_for('mna_companies.view_company', company_id=company_id))


@bp.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    return jsonify(search_mna_companies(q))
