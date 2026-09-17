from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.crm_notes import (HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note,
                                get_history, get_notes)
from models.mna_company import get_all_mna_companies
from models.mna_contact import (create_mna_contact, delete_mna_contact, get_all_mna_contacts,
                                  get_mna_contact_by_id, search_mna_contacts, set_starred,
                                  update_mna_contact)
from models.mna_deal import get_deals_for_contact

bp = Blueprint('mna_contacts', __name__, url_prefix='/mna/kontakty')


def _parse_form(form):
    return {
        'first_name': form.get('first_name', '').strip(),
        'last_name': form.get('last_name', '').strip(),
        'company_id': form.get('company_id', type=int),
        'position': form.get('position', '').strip(),
        'email': form.get('email', '').strip(),
        'phone': form.get('phone', '').strip(),
        'linkedin_url': form.get('linkedin_url', '').strip(),
        'description': form.get('description', '').strip(),
    }


def _validate(data):
    errors = []
    if not data.get('first_name') or not data.get('last_name'):
        errors.append('Imię i nazwisko są wymagane.')
    return errors


@bp.route('/')
def list_contacts():
    sort = request.args.get('sort', 'last_name')
    direction = request.args.get('dir', 'asc')
    search = request.args.get('search', '')
    company_id = request.args.get('company_id', type=int)
    contacts = get_all_mna_contacts(sort=sort, direction=direction, search=search or None, company_id=company_id)
    return render_template('mna_contacts/list.html',
        active_tab='mna_contacts', contacts=contacts, sort=sort, direction=direction,
        filters={'search': search, 'company_id': company_id})


@bp.route('/new', methods=['GET', 'POST'])
def new_contact():
    companies = get_all_mna_companies()
    preset_company_id = request.args.get('company_id', type=int)
    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_contacts/form.html',
                active_tab='mna_contacts', contact=request.form, companies=companies,
                action=url_for('mna_contacts.new_contact'), title='Nowy kontakt M&A')

        contact_id = create_mna_contact(data, session.get('user_id'))
        flash('Kontakt został zapisany.', 'success')
        return redirect(url_for('mna_contacts.view_contact', contact_id=contact_id))

    contact = {'company_id': preset_company_id} if preset_company_id else {}
    return render_template('mna_contacts/form.html',
        active_tab='mna_contacts', contact=contact, companies=companies,
        action=url_for('mna_contacts.new_contact'), title='Nowy kontakt M&A')


@bp.route('/<int:contact_id>/edit', methods=['GET', 'POST'])
def edit_contact(contact_id):
    contact = get_mna_contact_by_id(contact_id)
    if not contact:
        flash('Kontakt nie istnieje.', 'error')
        return redirect(url_for('mna_contacts.list_contacts'))

    companies = get_all_mna_companies()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_contacts/form.html',
                active_tab='mna_contacts', contact=request.form, companies=companies,
                action=url_for('mna_contacts.edit_contact', contact_id=contact_id), title='Edytuj kontakt M&A')

        update_mna_contact(contact_id, data, session.get('user_id'))
        flash('Kontakt został zaktualizowany.', 'success')
        return redirect(url_for('mna_contacts.view_contact', contact_id=contact_id))

    return render_template('mna_contacts/form.html',
        active_tab='mna_contacts', contact=contact, companies=companies,
        action=url_for('mna_contacts.edit_contact', contact_id=contact_id), title='Edytuj kontakt M&A')


@bp.route('/<int:contact_id>')
def view_contact(contact_id):
    contact = get_mna_contact_by_id(contact_id)
    if not contact:
        flash('Kontakt nie istnieje.', 'error')
        return redirect(url_for('mna_contacts.list_contacts'))

    deal_targets = get_deals_for_contact(contact_id)

    notes = get_notes('mna_contact', contact_id)
    for n in notes:
        n['delete_url'] = url_for('mna_contacts.delete_note_view', contact_id=contact_id, note_id=n['id'])
    history = get_history('mna_contact', contact_id)

    return render_template('mna_contacts/detail.html',
        active_tab='mna_contacts', contact=contact, deal_targets=deal_targets,
        notes=notes, history=history,
        add_note_url=url_for('mna_contacts.add_note_view', contact_id=contact_id),
        entity_type='mna_contact', entity_id=contact_id,
        note_type_labels=NOTE_TYPE_LABELS, history_badge_labels=HISTORY_BADGE_LABELS,
    )


@bp.route('/<int:contact_id>/toggle-star', methods=['POST'])
def toggle_star_view(contact_id):
    contact = get_mna_contact_by_id(contact_id)
    if contact:
        set_starred(contact_id, not contact.get('is_starred'))
    return redirect(url_for('mna_contacts.view_contact', contact_id=contact_id))


@bp.route('/<int:contact_id>/delete', methods=['POST'])
def delete_contact_view(contact_id):
    delete_mna_contact(contact_id, session.get('user_id'))
    flash('Kontakt został zarchiwizowany.', 'success')
    return redirect(url_for('mna_contacts.list_contacts'))


@bp.route('/<int:contact_id>/notes', methods=['POST'])
def add_note_view(contact_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('mna_contact', contact_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('mna_contacts.view_contact', contact_id=contact_id))


@bp.route('/<int:contact_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(contact_id, note_id):
    delete_note(note_id)
    return redirect(url_for('mna_contacts.view_contact', contact_id=contact_id))


@bp.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    return jsonify(search_mna_contacts(q))
