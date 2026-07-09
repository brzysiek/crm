"""Dopasowuje wynik parsowania Gemini (intencja + pola) do istniejących encji CRM
i wykonuje docelową akcję (notatka / utworzenie klienta, kontaktu, interesu)."""
import difflib

from models.agent_task import log_task
from models.crm_company import create_company, get_company_by_id, search_companies
from models.crm_contact import create_contact, get_contact_by_id, search_contacts
from models.crm_deal import create_deal, get_all_deals, get_deal_by_id
from models.crm_notes import add_note

_MATCH_THRESHOLD = 0.55


def _best_match(hint: str, candidates: list[dict], label_fn):
    if not hint or not candidates:
        return None
    hint_norm = hint.strip().lower()
    if not hint_norm:
        return None
    best, best_score = None, 0.0
    for c in candidates:
        label = label_fn(c).strip().lower()
        if not label:
            continue
        score = difflib.SequenceMatcher(None, hint_norm, label).ratio()
        if label == hint_norm:
            score = 1.0
        elif label.startswith(hint_norm) or hint_norm.startswith(label):
            score = max(score, 0.85)
        if score > best_score:
            best, best_score = c, score
    return best if best is not None and best_score >= _MATCH_THRESHOLD else None


def _company_label(c): return c.get('short_name') or c.get('name') or ''
def _contact_label(c): return f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
def _deal_label(d): return d.get('name') or ''


def _find_company(hint: str) -> dict | None:
    if not hint:
        return None
    return _best_match(hint, search_companies(hint, limit=8), _company_label)


def _find_contact(hint: str, company_id: int | None) -> dict | None:
    if not hint:
        return None
    match = _best_match(hint, search_contacts(hint, company_id=company_id, limit=8), _contact_label)
    if not match and company_id:
        match = _best_match(hint, search_contacts(hint, limit=8), _contact_label)
    return match


def _find_deal(hint: str) -> dict | None:
    if not hint:
        return None
    return _best_match(hint, get_all_deals(search=hint)[:8], _deal_label)


def _company_chip(c):
    return None if not c else {'id': c['id'], 'name': c.get('short_name') or c.get('name'),
                                'favicon_url': c.get('favicon_url')}


def _contact_chip(c):
    return None if not c else {'id': c['id'], 'name': _contact_label(c)}


def _deal_chip(d):
    return None if not d else {'id': d['id'], 'name': d.get('name')}


def resolve_intent(parsed: dict) -> dict:
    """Dopasowuje istniejące encje CRM po nazwie i zwraca strukturę do wyświetlenia
    w podsumowaniu (do ewentualnej ręcznej korekty) przed wykonaniem akcji."""
    intent = parsed['intent']
    entity_type = parsed['entity_type']
    fields = parsed['fields']

    out = {'intent': intent, 'entity_type': entity_type, 'fields': fields}

    if intent == 'note':
        if entity_type == 'company':
            match = _find_company(fields['company_name'])
            out['target'] = _company_chip(match)
            out['target_hint'] = fields['company_name']
        elif entity_type == 'contact':
            company_match = _find_company(fields['company_name']) if fields['company_name'] else None
            hint = f"{fields['first_name']} {fields['last_name']}".strip()
            match = _find_contact(hint, company_match['id'] if company_match else None)
            out['target'] = _contact_chip(match)
            out['target_hint'] = hint
            if match:
                out['context_company_name'] = match.get('company_name') or match.get('company_short_name')
            elif company_match:
                out['context_company_name'] = _company_label(company_match)
        else:
            match = _find_deal(fields['deal_name'])
            out['target'] = _deal_chip(match)
            out['target_hint'] = fields['deal_name']
            if match:
                if match.get('company_name'):
                    out['context_company_name'] = match.get('company_short_name') or match.get('company_name')
                if match.get('contact_first_name'):
                    out['context_contact_name'] = f"{match['contact_first_name']} {match['contact_last_name']}".strip()
        return out

    # intent == 'create'
    if entity_type == 'contact':
        company_match = _find_company(fields['company_name']) if fields['company_name'] else None
        out['link_company'] = _company_chip(company_match)
        out['link_company_hint'] = fields['company_name']
    elif entity_type == 'deal':
        company_match = _find_company(fields['company_name']) if fields['company_name'] else None
        hint = f"{fields['first_name']} {fields['last_name']}".strip()
        contact_match = _find_contact(hint, company_match['id'] if company_match else None) if hint else None
        out['link_company'] = _company_chip(company_match)
        out['link_company_hint'] = fields['company_name']
        out['link_contact'] = _contact_chip(contact_match)
        out['link_contact_hint'] = hint

    return out


def _entity_label_after(entity_type: str, entity_id: int) -> str:
    if entity_type == 'company':
        c = get_company_by_id(entity_id)
        return c['name'] if c else f'firma #{entity_id}'
    if entity_type == 'contact':
        c = get_contact_by_id(entity_id)
        return f"{c['first_name']} {c['last_name']}" if c else f'kontakt #{entity_id}'
    d = get_deal_by_id(entity_id)
    return d['name'] if d else f'interes #{entity_id}'


def execute_action(payload: dict, user_id: int | None) -> dict:
    """Wykonuje docelową akcję na podstawie (ewentualnie poprawionych przez użytkownika)
    danych z podsumowania. Rzuca ValueError z komunikatem dla użytkownika przy błędzie
    walidacji (nic nie jest wtedy zapisywane)."""
    intent = payload.get('intent')
    entity_type = payload.get('entity_type')
    fields = payload.get('fields') or {}
    input_text = (payload.get('input_text') or '').strip()

    if intent not in ('note', 'create') or entity_type not in ('company', 'contact', 'deal'):
        raise ValueError('Nieprawidłowe dane polecenia.')

    if intent == 'note':
        target_id = payload.get('target_id')
        if not target_id:
            raise ValueError('Nie wskazano, do czego dodać notatkę — wybierz firmę, kontakt lub interes.')
        body = (fields.get('note_body') or input_text).strip()
        if not body:
            raise ValueError('Treść notatki jest pusta.')
        add_note(entity_type, target_id, user_id, body)
        summary = f'Dodano notatkę do: {_entity_label_after(entity_type, target_id)}.'
        log_task(user_id, input_text, 'note', entity_type, target_id, summary)
        return {'summary': summary, 'entity_type': entity_type, 'entity_id': target_id}

    if entity_type == 'company':
        name = fields.get('company_name', '').strip()
        if not name:
            raise ValueError('Podaj nazwę firmy/klienta.')
        data = {
            'name': name,
            'city':        fields.get('city') or None,
            'email':       fields.get('email') or None,
            'phone':       fields.get('phone') or None,
            'website':     fields.get('website') or None,
            'nip':         fields.get('nip') or None,
            'description': fields.get('description') or None,
            'relation_type': 'lead',
        }
        source = [fields['source']] if fields.get('source') else None
        company_id = create_company(data, user_id, source=source)
        summary = f'Utworzono klienta „{name}”.'

        first_name = fields.get('first_name', '').strip()
        last_name = fields.get('last_name', '').strip()
        if first_name and last_name:
            create_contact({
                'company_id': company_id, 'first_name': first_name, 'last_name': last_name,
                'email': fields.get('email') or None, 'phone': fields.get('phone') or None,
                'description': fields.get('description') or None,
            }, user_id)
            summary += f' Dodano kontakt „{first_name} {last_name}”.'

        log_task(user_id, input_text, 'create', 'company', company_id, summary)
        return {'summary': summary, 'entity_type': 'company', 'entity_id': company_id}

    if entity_type == 'contact':
        first_name = fields.get('first_name', '').strip()
        last_name = fields.get('last_name', '').strip()
        if not first_name or not last_name:
            raise ValueError('Podaj imię i nazwisko kontaktu.')
        data = {
            'company_id': payload.get('link_company_id'),
            'first_name': first_name, 'last_name': last_name,
            'position':   fields.get('position') or None,
            'email':      fields.get('email') or None,
            'phone':      fields.get('phone') or None,
            'description': fields.get('description') or None,
        }
        contact_id = create_contact(data, user_id)
        summary = f'Utworzono kontakt „{first_name} {last_name}”.'
        log_task(user_id, input_text, 'create', 'contact', contact_id, summary)
        return {'summary': summary, 'entity_type': 'contact', 'entity_id': contact_id}

    # deal
    deal_name = fields.get('deal_name', '').strip() or 'Nowy interes'
    amount_raw = fields.get('amount', '').strip()
    try:
        amount_val = float(amount_raw.replace(',', '.').replace(' ', '')) if amount_raw else None
    except ValueError:
        amount_val = None
    data = {
        'name': deal_name,
        'description': fields.get('description') or None,
        'amount':      amount_val,
        'company_id':  payload.get('link_company_id'),
        'contact_id':  payload.get('link_contact_id'),
        'stage':       'new',
    }
    deal_id = create_deal(data, user_id)
    summary = f'Utworzono interes „{deal_name}”.'
    log_task(user_id, input_text, 'create', 'deal', deal_id, summary)
    return {'summary': summary, 'entity_type': 'deal', 'entity_id': deal_id}
