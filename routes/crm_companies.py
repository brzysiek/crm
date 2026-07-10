from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.crm_company import (RELATION_LABELS, create_company, delete_company,
                                  derive_short_name, get_all_companies,
                                  get_company_by_id, get_company_tags,
                                  set_starred, update_company)
from models.crm_file import get_files_for_company
from models.crm_notes import add_note, delete_note, get_history_multi, get_notes_multi
from models.user import get_active_users

bp = Blueprint('crm_companies', __name__, url_prefix='/crm/companies')


def _parse_form(form):
    name = form.get('name', '').strip()
    short_name = form.get('short_name', '').strip() or derive_short_name(name)
    return {
        'name': name,
        'short_name': short_name,
        'relation_type': form.get('relation_type', 'lead'),
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
        'owner_user_id': form.get('owner_user_id', type=int),
    }


def _validate(data):
    errors = []
    if not data.get('name'):
        errors.append('Nazwa firmy jest wymagana.')
    return errors


@bp.route('/')
def list_companies():
    sort = request.args.get('sort', 'created_at')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')
    relation_type = request.args.get('relation_type', '')
    tag = request.args.get('tag', '')
    industry = request.args.get('industry', '')
    source = request.args.get('source', '')

    companies = get_all_companies(
        sort=sort, direction=direction, search=search or None,
        relation_type=relation_type or None, tag=tag or None, industry=industry or None,
        source=source or None,
    )
    return render_template('crm/companies/list.html',
        active_tab='companies', companies=companies, relation_labels=RELATION_LABELS,
        sort=sort, direction=direction,
        filters={'search': search, 'relation_type': relation_type, 'tag': tag, 'industry': industry, 'source': source},
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_company():
    owners = get_active_users()
    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        tags = [t.strip() for t in request.form.getlist('tags[]') if t.strip()]
        industries = [t.strip() for t in request.form.getlist('industries[]') if t.strip()]
        source = [t.strip() for t in request.form.getlist('sources[]') if t.strip()]
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/companies/form.html',
                active_tab='companies', company=request.form, owners=owners, tags=tags, industries=industries,
                source=source,
                action=url_for('crm_companies.new_company'),
                title='Nowa firma', relation_labels=RELATION_LABELS)

        company_id = create_company(data, session.get('user_id'), tags=tags, industries=industries, source=source)

        contact_first_name = request.form.get('contact_first_name', '').strip()
        contact_last_name = request.form.get('contact_last_name', '').strip()
        if contact_first_name and contact_last_name:
            from models.crm_contact import create_contact
            create_contact({
                'company_id': company_id,
                'first_name': contact_first_name,
                'last_name': contact_last_name,
                'position': request.form.get('contact_position', '').strip() or None,
                'email': request.form.get('contact_email', '').strip() or None,
                'phone': request.form.get('contact_phone', '').strip() or None,
            }, session.get('user_id'))
            flash('Firma i kontakt zostały zapisane.', 'success')
        elif contact_first_name or contact_last_name:
            flash('Firma została zapisana, ale kontakt nie został utworzony — podaj imię i nazwisko.', 'error')
        else:
            flash('Firma została zapisana.', 'success')

        return redirect(url_for('crm_companies.view_company', company_id=company_id))

    return render_template('crm/companies/form.html',
        active_tab='companies', company={}, owners=owners, tags=[], industries=[], source=[],
        action=url_for('crm_companies.new_company'),
        title='Nowa firma', relation_labels=RELATION_LABELS)


@bp.route('/<int:company_id>/edit', methods=['GET', 'POST'])
def edit_company(company_id):
    company = get_company_by_id(company_id)
    if not company:
        flash('Firma nie istnieje.', 'error')
        return redirect(url_for('crm_companies.list_companies'))

    owners = get_active_users()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        tags = [t.strip() for t in request.form.getlist('tags[]') if t.strip()]
        industries = [t.strip() for t in request.form.getlist('industries[]') if t.strip()]
        source = [t.strip() for t in request.form.getlist('sources[]') if t.strip()]
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('crm/companies/form.html',
                active_tab='companies', company=request.form, owners=owners, tags=tags, industries=industries,
                source=source,
                action=url_for('crm_companies.edit_company', company_id=company_id),
                title='Edytuj firmę', relation_labels=RELATION_LABELS)

        update_company(company_id, data, session.get('user_id'), tags=tags, industries=industries, source=source)
        flash('Firma została zaktualizowana.', 'success')
        return redirect(url_for('crm_companies.view_company', company_id=company_id))

    from models.crm_contact import get_all_contacts

    return render_template('crm/companies/form.html',
        active_tab='companies', company=company, owners=owners,
        tags=get_company_tags(company_id, 'tag'),
        industries=get_company_tags(company_id, 'industry'),
        source=get_company_tags(company_id, 'source'),
        action=url_for('crm_companies.edit_company', company_id=company_id),
        title='Edytuj firmę', relation_labels=RELATION_LABELS,
        contacts_count=len(get_all_contacts(company_id=company_id)))


@bp.route('/<int:company_id>')
def view_company(company_id):
    company = get_company_by_id(company_id)
    if not company:
        flash('Firma nie istnieje.', 'error')
        return redirect(url_for('crm_companies.list_companies'))

    from models.crm_contact import get_all_contacts
    from models.crm_deal import get_all_deals, STAGE_BADGE_CLASSES, STAGE_LABELS

    contacts = get_all_contacts(company_id=company_id)
    deals = get_all_deals(company_id=company_id)
    contacts_by_id = {c['id']: c for c in contacts}
    deals_by_id = {d['id']: d for d in deals}

    entities = [('company', company_id)] + [('contact', c['id']) for c in contacts]
    notes = get_notes_multi(entities)
    for n in notes:
        n['_kind'] = 'note'
        if n['entity_type'] == 'company':
            n['source_label'] = 'Notatka firmy'
            n['delete_url'] = url_for('crm_companies.delete_note_view', company_id=company_id, note_id=n['id'])
        else:
            contact = contacts_by_id.get(n['entity_id'])
            contact_name = f"{contact['first_name']} {contact['last_name']}".strip() if contact else 'kontaktu'
            n['source_label'] = f'Notatka kontaktu: {contact_name}'
            n['delete_url'] = url_for('crm_contacts.delete_note_view', contact_id=n['entity_id'], note_id=n['id'])

    history_entities = entities + [('deal', d['id']) for d in deals]
    history = get_history_multi(history_entities)
    for h in history:
        h['_kind'] = 'history'
        if h['entity_type'] == 'company':
            h['source_label'] = None
        elif h['entity_type'] == 'contact':
            contact = contacts_by_id.get(h['entity_id'])
            contact_name = f"{contact['first_name']} {contact['last_name']}".strip() if contact else 'kontaktu'
            h['source_label'] = f'Kontakt: {contact_name}'
        else:
            deal = deals_by_id.get(h['entity_id'])
            h['source_label'] = f"Interes: {deal['name']}" if deal else 'Interes'

    activity = sorted(notes + history, key=lambda x: x['created_at'], reverse=True)

    street_line = ' '.join(filter(None, [company.get('street'), company.get('house_number')]))
    if company.get('flat_number'):
        street_line += f" lok. {company['flat_number']}"
    address = ', '.join(filter(None, [
        street_line or None, company.get('postal_code'), company.get('city'), company.get('country'),
    ]))

    return render_template('crm/companies/detail.html',
        active_tab='companies', company=company, relation_labels=RELATION_LABELS, address=address,
        tags=get_company_tags(company_id, 'tag'),
        industries=get_company_tags(company_id, 'industry'),
        source=get_company_tags(company_id, 'source'),
        contacts=contacts,
        deals=deals, stage_labels=STAGE_LABELS,
        stage_badge_classes=STAGE_BADGE_CLASSES,
        activity=activity,
        add_note_url=url_for('crm_companies.add_note_view', company_id=company_id),
        entity_type='company', entity_id=company_id,
        files=get_files_for_company(company_id),
        can_upload_files=True,
        upload_company_id=company_id,
        upload_contact_id=None,
    )


@bp.route('/<int:company_id>/toggle-star', methods=['POST'])
def toggle_star_view(company_id):
    company = get_company_by_id(company_id)
    if company:
        set_starred(company_id, not company.get('is_starred'))
    return redirect(url_for('crm_companies.view_company', company_id=company_id))


@bp.route('/<int:company_id>/delete', methods=['POST'])
def delete_company_view(company_id):
    archive_contacts = request.form.get('archive_contacts') == '1'
    delete_company(company_id, session.get('user_id'), archive_contacts=archive_contacts)
    flash('Firma została zarchiwizowana.', 'success')
    return redirect(url_for('crm_companies.list_companies'))


@bp.route('/<int:company_id>/notes', methods=['POST'])
def add_note_view(company_id):
    body = request.form.get('body', '').strip()
    if body:
        add_note('company', company_id, session.get('user_id'), body)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('crm_companies.view_company', company_id=company_id))


@bp.route('/<int:company_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(company_id, note_id):
    delete_note(note_id)
    return redirect(url_for('crm_companies.view_company', company_id=company_id))
