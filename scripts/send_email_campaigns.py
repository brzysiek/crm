"""Skrypt wysyłkowy kampanii email — odpalany cyklicznie z cPanel Cron Jobs
(np. co 2 minuty), nie jako trwały proces (hosting Passenger nie ma
Redis/Celery). Każde uruchomienie wysyła mały batch i kończy działanie.

Przykładowy wpis w cPanel Cron Jobs:
*/2 * * * * /home/<user>/virtualenv/.../bin/python /home/<user>/crm/scripts/send_email_campaigns.py >> /home/<user>/crm/logs/email_cron.log 2>&1
"""
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from app import app
from config import Config
from models.email_campaigns import (count_sent_today, get_campaign_by_id, get_pending_batch,
                                      is_unsubscribed, mark_failed, mark_sent,
                                      mark_skipped_unsubscribed, maybe_complete_campaign)
from models.settings import get_setting
from services.gmail_sender import GmailSender

SLEEP_BETWEEN_SENDS = 7  # sekundy, throttling wewnątrz jednego uruchomienia


def run():
    with app.app_context():
        daily_limit = int(get_setting('email_daily_limit', 150))
        sent_today = count_sent_today()
        if sent_today >= daily_limit:
            logger.info(f'Dzienny limit wysyłek osiągnięty ({sent_today}/{daily_limit}) — kończę.')
            return

        batch_size = min(int(get_setting('email_batch_per_run', 3)), daily_limit - sent_today)
        batch = get_pending_batch(batch_size)
        if not batch:
            logger.info('Brak oczekujących wiadomości.')
            return

        sender_email = get_setting('gmail_sender_email', '')
        api_token = get_setting('google_drive_api_token', '')
        if not sender_email or not api_token:
            logger.warning('Brak konfiguracji wysyłki (adres nadawcy / token konta usługi) — Ustawienia → Ogólne.')
            return

        sender = GmailSender(api_token, sender_email)
        campaign_ids = set()

        for i, recipient in enumerate(batch):
            campaign_ids.add(recipient['campaign_id'])
            if is_unsubscribed(recipient['email']):
                mark_skipped_unsubscribed(recipient['id'])
                logger.info(f"Pominięto (wypisany): {recipient['email']}")
                continue

            campaign = get_campaign_by_id(recipient['campaign_id'])
            unsubscribe_url = f"{Config.APP_BASE_URL}/email-campaigns/unsubscribe/{recipient['unsubscribe_token']}"

            try:
                message_id = sender.send(
                    to=recipient['email'],
                    subject=campaign['subject'],
                    body_text=campaign['body_text'],
                    unsubscribe_url=unsubscribe_url,
                )
                mark_sent(recipient['id'], message_id)
                logger.info(f"Wysłano: {recipient['email']} (id={message_id})")
            except Exception as e:
                mark_failed(recipient['id'], str(e))
                logger.error(f"Błąd wysyłki do {recipient['email']}: {e}")

            if i < len(batch) - 1:
                time.sleep(SLEEP_BETWEEN_SENDS)

        for campaign_id in campaign_ids:
            maybe_complete_campaign(campaign_id)


if __name__ == '__main__':
    run()
