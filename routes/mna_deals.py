from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.crm_file import get_files_for_mna_deal
from models.crm_mna_offer import get_all_mna_offers
from models.crm_notes import (HISTORY_BADGE_LABELS, NOTE_TYPE_LABELS, add_note, delete_note,
                                get_history, get_notes)
from models.mna_company import search_mna_companies
from models.mna_contact import search_mna_contacts
from models.mna_deal import (STAGE_BADGE_CLASSES, STAGE_LABELS, STAGE_ORDER, LIST_TYPE_LABELS,
                               INTEREST_STATUS_LABELS, add_target, create_mna_deal, delete_mna_deal,
                               get_all_mna_deals, get_mna_deal_by_id, get_targets_for_deal,
                               move_target_list, remove_target, reorder_targets, restore_mna_deal,
                               set_target_interest, set_target_score, set_target_valuable, update_mna_deal)
from routes.crm_contacts import build_gtd_items

bp = Blueprint('mna_deals', __name__, url_prefix='/mna/deals')


def _parse_form(form):
    return {
        'name': form.get('name', '').strip(),
        'description': form.get('description', '').strip(),
        'offer_id': form.get('offer_id', type=int),
        'stage': form.get('stage', 'long_list'),
        'amount': form.get('amount') or None,
        'start_date': form.get('start_date') or None,
        'end_date': form.get('end_date') or None,
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
    deals = get_all_mna_deals(sort=sort, direction=direction, search=search or None, stage=stage or None)
    return render_template('mna_deals/list.html',
        active_tab='mna_deals', deals=deals, sort=sort, direction=direction,
        filters={'search': search, 'stage': stage},
        stage_labels=STAGE_LABELS, stage_order=STAGE_ORDER, stage_badge_classes=STAGE_BADGE_CLASSES)


@bp.route('/new', methods=['GET', 'POST'])
def new_deal():
    offers = get_all_mna_offers()
    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_deals/form.html',
                active_tab='mna_deals', deal=request.form, offers=offers, stage_labels=STAGE_LABELS,
                stage_order=STAGE_ORDER, action=url_for('mna_deals.new_deal'), title='Nowy deal M&A')

        deal_id = create_mna_deal(data, session.get('user_id'))
        flash('Deal został zapisany.', 'success')
        return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))

    return render_template('mna_deals/form.html',
        active_tab='mna_deals', deal={}, offers=offers, stage_labels=STAGE_LABELS,
        stage_order=STAGE_ORDER, action=url_for('mna_deals.new_deal'), title='Nowy deal M&A')


@bp.route('/<int:deal_id>/edit', methods=['GET', 'POST'])
def edit_deal(deal_id):
    deal = get_mna_deal_by_id(deal_id)
    if not deal:
        flash('Deal nie istnieje.', 'error')
        return redirect(url_for('mna_deals.list_deals'))

    offers = get_all_mna_offers()

    if request.method == 'POST':
        data = _parse_form(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('mna_deals/form.html',
                active_tab='mna_deals', deal=request.form, offers=offers, stage_labels=STAGE_LABELS,
                stage_order=STAGE_ORDER, action=url_for('mna_deals.edit_deal', deal_id=deal_id),
                title='Edytuj deal M&A')

        update_mna_deal(deal_id, data, session.get('user_id'))
        flash('Deal został zaktualizowany.', 'success')
        return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))

    return render_template('mna_deals/form.html',
        active_tab='mna_deals', deal=deal, offers=offers, stage_labels=STAGE_LABELS,
        stage_order=STAGE_ORDER, action=url_for('mna_deals.edit_deal', deal_id=deal_id),
        title='Edytuj deal M&A')


@bp.route('/<int:deal_id>')
def view_deal(deal_id):
    deal = get_mna_deal_by_id(deal_id)
    if not deal:
        flash('Deal nie istnieje.', 'error')
        return redirect(url_for('mna_deals.list_deals'))

    long_list = get_targets_for_deal(deal_id, 'long_list')
    short_list = get_targets_for_deal(deal_id, 'short_list')

    notes = get_notes('mna_deal', deal_id)
    for n in notes:
        n['delete_url'] = url_for('mna_deals.delete_note_view', deal_id=deal_id, note_id=n['id'])
    history = get_history('mna_deal', deal_id)

    return render_template('mna_deals/detail.html',
        active_tab='mna_deals', deal=deal, long_list=long_list, short_list=short_list,
        stage_labels=STAGE_LABELS, stage_order=STAGE_ORDER, stage_badge_classes=STAGE_BADGE_CLASSES,
        list_type_labels=LIST_TYPE_LABELS, interest_status_labels=INTEREST_STATUS_LABELS,
        notes=notes, history=history,
        files=get_files_for_mna_deal(deal_id),
        can_upload_files=True,
        upload_company_id=None,
        upload_contact_id=None,
        upload_mna_deal_id=deal_id,
        add_note_url=url_for('mna_deals.add_note_view', deal_id=deal_id),
        entity_type='mna_deal', entity_id=deal_id,
        note_type_labels=NOTE_TYPE_LABELS, history_badge_labels=HISTORY_BADGE_LABELS,
        gtd_items=build_gtd_items(mna_deal_id=deal_id),
    )


@bp.route('/<int:deal_id>/delete', methods=['POST'])
def delete_deal_view(deal_id):
    delete_mna_deal(deal_id, session.get('user_id'))
    flash('Deal został zarchiwizowany.', 'success')
    return redirect(url_for('mna_deals.list_deals'))


@bp.route('/<int:deal_id>/restore', methods=['POST'])
def restore_deal_view(deal_id):
    restore_mna_deal(deal_id, session.get('user_id'))
    flash('Deal został przywrócony.', 'success')
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/notes', methods=['POST'])
def add_note_view(deal_id):
    body = request.form.get('body', '').strip()
    note_type = request.form.get('note_type', 'other')
    if body:
        add_note('mna_deal', deal_id, session.get('user_id'), body, note_type=note_type)
        flash('Notatka została dodana.', 'success')
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/notes/<int:note_id>/delete', methods=['POST'])
def delete_note_view(deal_id, note_id):
    delete_note(note_id)
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


# ── Long lista / short lista — zarządzanie pozycjami ────────────────────────

@bp.route('/<int:deal_id>/targets', methods=['POST'])
def add_target_view(deal_id):
    list_type = request.form.get('list_type', 'long_list')
    company_id = request.form.get('company_id', type=int)
    contact_id = request.form.get('contact_id', type=int)
    if not company_id and not contact_id:
        flash('Wybierz firmę lub kontakt do dodania.', 'error')
    else:
        add_target(deal_id, company_id, contact_id, list_type, session.get('user_id'))
        flash('Dodano pozycję do listy.', 'success')
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/<int:target_id>/remove', methods=['POST'])
def remove_target_view(deal_id, target_id):
    remove_target(target_id, session.get('user_id'))
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/<int:target_id>/move', methods=['POST'])
def move_target_view(deal_id, target_id):
    list_type = request.form.get('list_type', 'long_list')
    move_target_list(target_id, list_type, session.get('user_id'))
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/<int:target_id>/interest', methods=['POST'])
def set_target_interest_view(deal_id, target_id):
    interest_status = request.form.get('interest_status', 'unknown')
    set_target_interest(target_id, interest_status, session.get('user_id'))
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/<int:target_id>/valuable', methods=['POST'])
def set_target_valuable_view(deal_id, target_id):
    is_valuable = request.form.get('is_valuable') == '1'
    set_target_valuable(target_id, is_valuable, session.get('user_id'))
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/<int:target_id>/score', methods=['POST'])
def set_target_score_view(deal_id, target_id):
    raw = request.form.get('score', '').strip()
    score = int(raw) if raw else None
    if score is not None:
        score = max(1, min(100, score))
    set_target_score(target_id, score, session.get('user_id'))
    return redirect(url_for('mna_deals.view_deal', deal_id=deal_id))


@bp.route('/<int:deal_id>/targets/reorder', methods=['POST'])
def reorder_targets_view(deal_id):
    ordered_ids = request.form.getlist('target_id', type=int)
    reorder_targets(deal_id, ordered_ids)
    return jsonify({'ok': True})


@bp.route('/api/search-target-companies')
def api_search_target_companies():
    q = request.args.get('q', '')
    return jsonify(search_mna_companies(q))


@bp.route('/api/search-target-contacts')
def api_search_target_contacts():
    q = request.args.get('q', '')
    return jsonify(search_mna_contacts(q))
