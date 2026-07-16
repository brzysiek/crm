import unicodedata
from datetime import date, datetime
from urllib.parse import quote

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for

import models.gcal_event as gcal_event_model
import models.task as task_model
from models.crm_company import (RELATION_LABELS, get_companies_referred_by_company,
                                  get_companies_referred_by_contact,
                                  get_company_by_id, get_company_tags)
from models.crm_contact import (create_contact, delete_contact, get_all_contacts,
                                  get_contact_by_id, set_starred, update_contact)
from models.crm_file import get_files_for_company
from models.crm_notes import (HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note,
                                get_history_multi, get_notes_multi)
from services.vcard import build_vcard

bp = Blueprint('crm_contacts', __name__, url_prefix='/crm/contacts')


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def build_gtd_items(contact_id=None, company_id=None):
    """Zadania/projekty/spotkania przypisane do kontaktu lub firmy CRM — sekcja
    „Zadania/Projekty/Spotkania” na karcie kontaktu/firmy (współdzielone z
    crm_companies.view_company)."""
    tasks = task_model.get_tasks_for_crm(contact_id=contact_id, company_id=company_id)
    events = gcal_event_model.enrich_with_titles(
        gcal_event_model.get_events_for_crm(contact_id=contact_id, company_id=company_id)
    )

    items = []
    for t in tasks:
        sort_date = _as_date(t['completed_at']) or t['due_date'] or _as_date(t['created_at'])
        items.append({
            'kind': 'project' if t['is_project'] else 'task',
            'title': t['title'],
            'done': t['status'] == 'done',
            'date': sort_date,
            'url': url_for('gtd.project_detail', project_id=t['id']) if t['is_project'] else None,
        })
    for e in events:
        if not e.get('title'):
            continue
        items.append({
            'kind': 'event',
            'title': e['title'],
            'done': e['done_at'] is not None,
            'date': _as_date(e['done_at']) or e['event_date'],
            'url': None,
        })
    items.sort(key=lambda x: x['date'] or date.min, reverse=True)
    return items


def _parse_form(form):
    return {
        'first_name': form.get('first_name', '').strip(),
        'last_name': form.get('last_name', '').strip(),
        'position': form.get('position', '').strip(),
        'email': form.get('email', '').strip(),
        'phone': form.get('phone', '').strip(),
        'linkedin_url': form.get('linkedin_url', '').strip(),
        'description': form.get('description', '').strip(),
        'company_id': form.get('company_id', type=int),
    }


def _validate(data):
    errors = []
    if not data.get('first_name'):
        errors.append('Imię jest wymagane.')
    if not data.get('last_name'):
        errors.append('Nazwisko jest wymagane.')
    return errors


@bp.route('/')
def list_contacts():
    sort = request.args.get('sort', 'created_at')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')

    contacts = get_all_contacts(sort=sort, direction=direction, search=search or None)
    return render_template('crm/contacts/list.html',
        active_tab='contacts', contacts=contacts,
        sort=sort, direction=direction, filters={'search': search},
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_contact():
    prefill_company = None
    company_id = request.args.get('company_id', type=int)
    if company_id:
        prefill_company = get_company_by_id(company_id)

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/contacts/form.html',
                active_tab='contacts', contact=request.form, prefill_company=None,
                action=url_for('crm_contacts.new_contact'), title='Nowy kontakt')

        contact_id = create_contact(data, session.get('user_id'))
        flash('Kontakt został zapisany.', 'success')
        return redirect(url_for('crm_contacts.view_contact', contact_id=contact_id))

    return render_template('crm/contacts/form.html',
        active_tab='contacts', contact={'company_id': company_id} if company_id else {},
        prefill_company=prefill_company,
        action=url_for('crm_contacts.new_contact'), title='Nowy kontakt')


@bp.route('/<int:contact_id>/edit', methods=['GET', 'POST'])
def edit_contact(contact_id):
    contact = get_contact_by_id(contact_id)
    if not contact:
        flash('Kontakt nie istnieje.', 'error')
        return redirect(url_for('crm_contacts.list_contacts'))

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/contacts/form.html',
                active_tab='contacts', contact=request.form, prefill_company=None,
                action=url_for('crm_contacts.edit_contact', contact_id=contact_id),
                title='Edytuj kontakt')

        update_contact(contact_id, data, session.get('user_id'))
        flash('Kontakt został zaktualizowany.', 'success')
        return redirect(url_for('crm_contacts.view_contact', contact_id=contact_id))

    prefill_company = get_company_by_id(contact['company_id']) if contact.get('company_id') else None
    return render_template('crm/contacts/form.html',
        active_tab='contacts', contact=contact, prefill_company=prefill_company,
        action=url_for('crm_contacts.edit_contact', contact_id=contact_id),
        title='Edytuj kontakt')


@bp.route('/<int:contact_id>')
def view_contact(contact_id):
    contact = get_contact_by_id(contact_id)
    if not contact:
        flash('Kontakt nie istnieje.', 'error')
        return redirect(url_for('crm_contacts.list_contacts'))

    from models.crm_deal import get_all_deals, STAGE_BADGE_CLASSES, STAGE_LABELS
    from models.crm_file import get_business_card

    company_tags = []
    company_industries = []
    company_source = []
    if contact.get('company_id'):
        company_tags = get_company_tags(contact['company_id'], 'tag')
        company_industries = get_company_tags(contact['company_id'], 'industry')
        company_source = get_company_tags(contact['company_id'], 'source')

    company = get_company_by_id(contact['company_id']) if contact.get('company_id') else None
    deals = get_all_deals(contact_id=contact_id)

    entities = [('contact', contact_id)]
    if company:
        entities.append(('company', company['id']))
    notes = get_notes_multi(entities)
    for n in notes:
        n['_kind'] = 'note'
        if n['entity_type'] == 'contact':
            n['source_label'] = 'Notatka kontaktu'
            n['delete_url'] = url_for('crm_contacts.delete_note_view', contact_id=contact_id, note_id=n['id'])
        else:
            n['source_label'] = 'Notatka firmy'
            n['delete_url'] = url_for('crm_companies.delete_note_view', company_id=n['entity_id'], note_id=n['id'])

    history_entities = entities + [('deal', d['id']) for d in deals]
    history = get_history_multi(history_entities)
    for h in history:
        h['_kind'] = 'history'
        if h['entity_type'] == 'contact':
            h['source_label'] = None
        elif h['entity_type'] == 'company':
            h['source_label'] = 'Firma'
        else:
            deal = next((d for d in deals if d['id'] == h['entity_id']), None)
            h['source_label'] = f"Deal: {deal['name']}" if deal else 'Deal'

    activity = sorted(notes + history, key=lambda x: x['created_at'], reverse=True)
    referred_by_id = {c['id']: c for c in get_companies_referred_by_contact(contact_id)}
    if contact.get('company_id'):
        for c in get_companies_referred_by_company(contact['company_id']):
            referred_by_id.setdefault(c['id'], c)
    referred_companies = sorted(referred_by_id.values(), key=lambda c: c['created_at'], reverse=True)

    return render_template('crm/contacts/detail.html',
        active_tab='contacts', contact=contact, company=company, company_tags=company_tags,
        company_industries=company_industries, company_source=company_source, relation_labels=RELATION_LABELS,
        deals=deals, stage_labels=STAGE_LABELS,
        referred_companies=referred_companies,
        stage_badge_classes=STAGE_BADGE_CLASSES,
        activity=activity,
        add_note_url=url_for('crm_contacts.add_note_view', contact_id=contact_id),
        entity_type='contact', entity_id=contact_id,
        files=get_files_for_company(company['id']) if company else [],
        can_upload_files=bool(company),
        upload_company_id=company['id'] if company else None,
        upload_contact_id=contact_id,
        business_card=get_business_card(contact_id),
        note_type_labels=NOTE_TYPE_LABELS,
        history_badge_labels=HISTORY_BADGE_LABELS,
        gtd_items=build_gtd_items(contact_id=contact_id),
    )


@bp.route('/<int:contact_id>/vcard')
def download_vcard(contact_id):
    contact = get_contact_by_id(contact_id)
    if not contact:
        flash('Kontakt nie istnieje.', 'error')
        return redirect(url_for('crm_contacts.list_contacts'))

    vcard = build_vcard(contact)
    display_name = f"{contact['first_name']} {contact['last_name']}".strip().replace(' ', '_') or 'kontakt'
    ascii_name = unicodedata.normalize('NFKD', display_name).encode('ascii', 'ignore').decode('ascii') or 'kontakt'

    return Response(vcard, mimetype='text/vcard', headers={
        'Content-Disposition': (
            f'attachment; filename="{ascii_name}.vcf"; '
            f"filename*=UTF-8''{quote(display_name)}.vcf"
        )
    })


@bp.route('/<int:contact_id>/toggle-star', methods=['POST'])
def toggle_star_view(contact_id):
    contact = get_contact_by_id(contact_id)
    if contact:
        set_starred(contact_id, not contact.get('is_starred'))
    return redirect(url_for('crm_contacts.view_contact', contact_id=contact_id))


@bp.route('/<int:contact_id>/delete', methods=['POST'])
def delete_contact_view(contact_id):
    archive_company = request.form.get('archive_company') == '1'
    delete_contact(contact_id, session.get('user_id'), archive_company=archive_company)
    flash('Kontakt został zarchiwizowany.', 'success')
    return redirect(url_for('crm_contacts.list_contacts'))


@bp.route('/<int:contact_id>/notes', methods=['POST'])
def add_note_view(contact_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('contact', contact_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('crm_contacts.view_contact', contact_id=contact_id))


@bp.route('/<int:contact_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(contact_id, note_id):
    delete_note(note_id)
    return redirect(url_for('crm_contacts.view_contact', contact_id=contact_id))
