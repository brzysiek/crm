from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.crm_company import get_company_by_id
from models.crm_contact import get_contact_by_id
from models.crm_file import get_files_for_mna_offer
from models.crm_mna_offer import (FIELD_LABELS, OFFER_TYPE_BADGE_CLASSES, OFFER_TYPE_LABELS,
                                   create_mna_offer, delete_mna_offer, get_all_mna_offers,
                                   get_deleted_mna_offers, get_mna_offer_by_id,
                                   next_mna_offer_ref, permanently_delete_mna_offer, restore_mna_offer,
                                   update_mna_offer)
from models.crm_notes import HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note, get_history, get_notes
from models.user import get_active_users
from routes.crm_contacts import build_gtd_items

bp = Blueprint('mna_offers', __name__, url_prefix='/mna')


def _parse_form(form):
    try:
        revenue = float((form.get('revenue', '') or '').replace(',', '.')) if form.get('revenue') else None
    except ValueError:
        revenue = None
    try:
        ebitda = float((form.get('ebitda', '') or '').replace(',', '.')) if form.get('ebitda') else None
    except ValueError:
        ebitda = None
    return {
        'name': form.get('name', '').strip(),
        'ref_number': form.get('ref_number', '').strip()[:20],
        'description': form.get('description', '').strip(),
        'industry': form.get('industry', '').strip(),
        'revenue': revenue,
        'ebitda': ebitda,
        'offer_type': form.get('offer_type', 'for_sale'),
        'added_date': form.get('added_date', '').strip() or None,
        'target_contact_id': form.get('target_contact_id', type=int),
        'target_company_id': form.get('target_company_id', type=int),
        'source_contact_id': form.get('source_contact_id', type=int),
        'source_company_id': form.get('source_company_id', type=int),
        'owner_user_id': form.get('owner_user_id', type=int),
    }


def _validate(data):
    errors = []
    if not data.get('name'):
        errors.append('Nazwa oferty jest wymagana.')
    return errors


@bp.route('/na-sprzedaz')
def list_for_sale():
    sort = request.args.get('sort', 'created_at')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')
    offers = get_all_mna_offers(offer_type='for_sale', sort=sort, direction=direction, search=search or None)
    return render_template('mna_offers/list.html',
        active_tab='mna_offers_for_sale', offers=offers, offer_type='for_sale',
        offer_type_labels=OFFER_TYPE_LABELS, offer_type_badge_classes=OFFER_TYPE_BADGE_CLASSES,
        sort=sort, direction=direction, filters={'search': search},
        list_title='Oferty M&A — firmy na sprzedaż',
        new_url=url_for('mna_offers.new_mna_offer', offer_type='for_sale'),
    )


@bp.route('/poszukiwane')
def list_wanted():
    sort = request.args.get('sort', 'created_at')
    direction = request.args.get('dir', 'desc')
    search = request.args.get('search', '')
    offers = get_all_mna_offers(offer_type='wanted', sort=sort, direction=direction, search=search or None)
    return render_template('mna_offers/list.html',
        active_tab='mna_offers_wanted', offers=offers, offer_type='wanted',
        offer_type_labels=OFFER_TYPE_LABELS, offer_type_badge_classes=OFFER_TYPE_BADGE_CLASSES,
        sort=sort, direction=direction, filters={'search': search},
        list_title='Oferty M&A — firmy poszukiwane',
        new_url=url_for('mna_offers.new_mna_offer', offer_type='wanted'),
    )


@bp.route('/new', methods=['GET', 'POST'])
def new_mna_offer():
    owners = get_active_users()
    offer_type = request.args.get('offer_type', 'for_sale')

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_offers/form.html',
                active_tab='mna_offers', offer=request.form, owners=owners,
                offer_type_labels=OFFER_TYPE_LABELS,
                prefill_target_company=None, prefill_target_contact=None,
                prefill_source_company=None, prefill_source_contact=None,
                action=url_for('mna_offers.new_mna_offer'), title='Nowa oferta M&A')

        if not data.get('added_date'):
            data['added_date'] = date.today().isoformat()
        offer_id = create_mna_offer(data, session.get('user_id'))
        flash('Oferta M&A została zapisana.', 'success')
        return redirect(url_for('mna_offers.view_mna_offer', offer_id=offer_id))

    return render_template('mna_offers/form.html',
        active_tab='mna_offers',
        offer={'offer_type': offer_type, 'added_date': date.today().isoformat(),
               'ref_number': next_mna_offer_ref()},
        owners=owners,
        offer_type_labels=OFFER_TYPE_LABELS,
        prefill_target_company=None, prefill_target_contact=None,
        prefill_source_company=None, prefill_source_contact=None,
        action=url_for('mna_offers.new_mna_offer'), title='Nowa oferta M&A')


@bp.route('/<int:offer_id>/edit', methods=['GET', 'POST'])
def edit_mna_offer(offer_id):
    offer = get_mna_offer_by_id(offer_id)
    if not offer:
        flash('Oferta M&A nie istnieje.', 'error')
        return redirect(url_for('mna_offers.list_for_sale'))

    owners = get_active_users()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_offers/form.html',
                active_tab='mna_offers', offer=request.form, owners=owners,
                offer_type_labels=OFFER_TYPE_LABELS,
                prefill_target_company=None, prefill_target_contact=None,
                prefill_source_company=None, prefill_source_contact=None,
                action=url_for('mna_offers.edit_mna_offer', offer_id=offer_id), title='Edytuj ofertę M&A')

        update_mna_offer(offer_id, data, session.get('user_id'))
        flash('Oferta M&A została zaktualizowana.', 'success')
        return redirect(url_for('mna_offers.view_mna_offer', offer_id=offer_id))

    if not offer.get('ref_number'):
        # Oferty sprzed wprowadzenia numeracji dostają propozycję numeru na bieżący miesiąc.
        offer = {**offer, 'ref_number': next_mna_offer_ref()}
    prefill_target_company = get_company_by_id(offer['target_company_id']) if offer.get('target_company_id') else None
    prefill_target_contact = get_contact_by_id(offer['target_contact_id']) if offer.get('target_contact_id') else None
    prefill_source_company = get_company_by_id(offer['source_company_id']) if offer.get('source_company_id') else None
    prefill_source_contact = get_contact_by_id(offer['source_contact_id']) if offer.get('source_contact_id') else None
    return render_template('mna_offers/form.html',
        active_tab='mna_offers', offer=offer, owners=owners,
        offer_type_labels=OFFER_TYPE_LABELS,
        prefill_target_company=prefill_target_company, prefill_target_contact=prefill_target_contact,
        prefill_source_company=prefill_source_company, prefill_source_contact=prefill_source_contact,
        action=url_for('mna_offers.edit_mna_offer', offer_id=offer_id), title='Edytuj ofertę M&A')


@bp.route('/<int:offer_id>')
def view_mna_offer(offer_id):
    offer = get_mna_offer_by_id(offer_id)
    if not offer:
        flash('Oferta M&A nie istnieje.', 'error')
        return redirect(url_for('mna_offers.list_for_sale'))

    notes = get_notes('mna_offer', offer_id)
    for n in notes:
        n['delete_url'] = url_for('mna_offers.delete_note_view', offer_id=offer_id, note_id=n['id'])

    return render_template('mna_offers/detail.html',
        active_tab='mna_offers', offer=offer,
        offer_type_labels=OFFER_TYPE_LABELS, offer_type_badge_classes=OFFER_TYPE_BADGE_CLASSES,
        notes=notes,
        history=get_history('mna_offer', offer_id),
        add_note_url=url_for('mna_offers.add_note_view', offer_id=offer_id),
        entity_type='mna_offer', entity_id=offer_id,
        note_type_labels=NOTE_TYPE_LABELS,
        history_badge_labels=HISTORY_BADGE_LABELS,
        gtd_items=build_gtd_items(mna_offer_id=offer_id),
        files=get_files_for_mna_offer(offer_id),
        can_upload_files=True,
        upload_company_id=None,
        upload_contact_id=None,
        upload_mna_deal_id=None,
        upload_mna_offer_id=offer_id,
    )


@bp.route('/<int:offer_id>/delete', methods=['POST'])
def delete_mna_offer_view(offer_id):
    offer = get_mna_offer_by_id(offer_id)
    delete_mna_offer(offer_id, session.get('user_id'))
    flash('Oferta M&A została zarchiwizowana.', 'success')
    if offer and offer.get('offer_type') == 'wanted':
        return redirect(url_for('mna_offers.list_wanted'))
    return redirect(url_for('mna_offers.list_for_sale'))


@bp.route('/archiwum')
def archive():
    return render_template('mna_offers/archive.html',
        active_tab='mna_offers', offers=get_deleted_mna_offers(),
        offer_type_labels=OFFER_TYPE_LABELS, offer_type_badge_classes=OFFER_TYPE_BADGE_CLASSES,
    )


@bp.route('/<int:offer_id>/restore', methods=['POST'])
def restore_mna_offer_view(offer_id):
    restore_mna_offer(offer_id, session.get('user_id'))
    flash('Oferta M&A została przywrócona.', 'success')
    return redirect(url_for('mna_offers.archive'))


@bp.route('/<int:offer_id>/permanent-delete', methods=['POST'])
def permanently_delete_mna_offer_view(offer_id):
    permanently_delete_mna_offer(offer_id, session.get('user_id'))
    flash('Oferta M&A została trwale usunięta.', 'success')
    return redirect(url_for('mna_offers.archive'))


@bp.route('/<int:offer_id>/notes', methods=['POST'])
def add_note_view(offer_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('mna_offer', offer_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('mna_offers.view_mna_offer', offer_id=offer_id))


@bp.route('/<int:offer_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(offer_id, note_id):
    delete_note(note_id)
    return redirect(url_for('mna_offers.view_mna_offer', offer_id=offer_id))
