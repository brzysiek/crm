from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.crm_tags import get_or_create_tag_ids, get_tag_ids_by_names
from models.email_campaigns import (add_unsubscribe, create_campaign, freeze_recipients,
                                      get_all_campaigns, get_campaign_by_id, get_campaign_recipients,
                                      get_campaign_tag_names, get_recipient_by_token,
                                      resolve_recipient_contacts)

bp = Blueprint('email_campaigns', __name__, url_prefix='/email-campaigns')

STATUS_LABELS = {'draft': 'Szkic', 'sending': 'Wysyłanie', 'sent': 'Wysłano'}
STATUS_BADGES = {'draft': 'badge-gray', 'sending': 'badge-yellow', 'sent': 'badge-green'}
RECIPIENT_STATUS_LABELS = {
    'pending': 'Oczekuje', 'sent': 'Wysłano', 'failed': 'Błąd',
    'skipped_unsubscribed': 'Pominięto (wypisany)',
}
RECIPIENT_STATUS_BADGES = {
    'pending': 'badge-gray', 'sent': 'badge-green', 'failed': 'badge-red',
    'skipped_unsubscribed': 'badge-blue',
}


@bp.route('/')
def list_campaigns():
    return render_template('email_campaigns/list.html',
        active_tab='email_campaigns', campaigns=get_all_campaigns(),
        status_labels=STATUS_LABELS, status_badges=STATUS_BADGES)


@bp.route('/new', methods=['GET', 'POST'])
def new_campaign():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        body_text = request.form.get('body_text', '').strip()
        tag_names = [t.strip() for t in request.form.getlist('tags[]') if t.strip()]

        errors = []
        if not name:
            errors.append('Nazwa kampanii jest wymagana.')
        if not subject:
            errors.append('Temat wiadomości jest wymagany.')
        if not body_text:
            errors.append('Treść wiadomości jest wymagana.')
        if not tag_names:
            errors.append('Wybierz co najmniej jeden tag odbiorców.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('email_campaigns/form.html',
                active_tab='email_campaigns', campaign=request.form, tags=tag_names,
                action=url_for('email_campaigns.new_campaign'), title='Nowa kampania')

        tag_ids = get_or_create_tag_ids('tag', tag_names)
        campaign_id = create_campaign(name, subject, body_text, tag_ids, session.get('user_id'))
        flash('Kampania została zapisana jako szkic.', 'success')
        return redirect(url_for('email_campaigns.view_campaign', campaign_id=campaign_id))

    return render_template('email_campaigns/form.html',
        active_tab='email_campaigns', campaign={}, tags=[],
        action=url_for('email_campaigns.new_campaign'), title='Nowa kampania')


@bp.route('/<int:campaign_id>')
def view_campaign(campaign_id):
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        flash('Kampania nie istnieje.', 'error')
        return redirect(url_for('email_campaigns.list_campaigns'))

    recipients = get_campaign_recipients(campaign_id)
    counts = {'pending': 0, 'sent': 0, 'failed': 0, 'skipped_unsubscribed': 0}
    for r in recipients:
        counts[r['status']] = counts.get(r['status'], 0) + 1

    return render_template('email_campaigns/detail.html',
        active_tab='email_campaigns', campaign=campaign, recipients=recipients, counts=counts,
        tag_names=get_campaign_tag_names(campaign_id),
        status_labels=STATUS_LABELS, status_badges=STATUS_BADGES,
        recipient_status_labels=RECIPIENT_STATUS_LABELS, recipient_status_badges=RECIPIENT_STATUS_BADGES)


@bp.route('/<int:campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        flash('Kampania nie istnieje.', 'error')
        return redirect(url_for('email_campaigns.list_campaigns'))
    if campaign['status'] != 'draft':
        flash('Ta kampania została już wysłana lub jest w trakcie wysyłki.', 'error')
        return redirect(url_for('email_campaigns.view_campaign', campaign_id=campaign_id))

    count = freeze_recipients(campaign_id)
    if count == 0:
        flash('Brak odbiorców spełniających warunki (tag, zgoda marketingowa, brak wypisania) — kampania nie została uruchomiona.', 'error')
    else:
        flash(f'Wysyłka uruchomiona — {count} odbiorców w kolejce. Maile będą wysyłane stopniowo przez cron.', 'success')
    return redirect(url_for('email_campaigns.view_campaign', campaign_id=campaign_id))


@bp.route('/api/preview-count')
def preview_count():
    tag_names = [t.strip() for t in request.args.get('tags', '').split(',') if t.strip()]
    if not tag_names:
        return jsonify({'status': 'ok', 'count': 0})
    tag_ids = get_tag_ids_by_names('tag', tag_names)
    count = len(resolve_recipient_contacts(tag_ids))
    return jsonify({'status': 'ok', 'count': count})


@bp.route('/unsubscribe/<token>')
def unsubscribe(token):
    recipient = get_recipient_by_token(token)
    if recipient:
        add_unsubscribe(recipient['email'], recipient['campaign_id'])
    return render_template('unsubscribe.html', found=bool(recipient))
