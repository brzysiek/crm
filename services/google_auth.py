"""Wspólna logika JWT service-account OAuth2 dla Google API (Drive, Calendar, ...).

Bez dodatkowych zależności — podpis JWT liczony przez `cryptography` (już w
requirements.txt). Token cache'owany per (client_email, private_key_id, scope).
"""
import base64
import json
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

TIMEOUT = 20

# { (client_email, private_key_id, scope) → (access_token, expires_at) }
_token_cache: dict = {}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def get_service_account_token(sa_json: dict, scope: str) -> str:
    """Zwraca ważny token OAuth2 dla konta usługi, dla podanego zakresu (scope).

    Tokeny cache'owane przez 55 minut (Google wydaje tokeny na 1h).
    """
    client_email = sa_json['client_email']
    private_key_id = sa_json.get('private_key_id', '')
    cache_key = (client_email, private_key_id, scope)

    cached = _token_cache.get(cache_key)
    if cached:
        token, expires_at = cached
        if time.time() < expires_at:
            return token

    now = int(time.time())
    header = {'alg': 'RS256', 'typ': 'JWT', 'kid': private_key_id}
    payload = {
        'iss': client_email,
        'sub': client_email,
        'scope': scope,
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': now,
        'exp': now + 3600,
    }

    header_b64  = _b64url(json.dumps(header,  separators=(',', ':')).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f'{header_b64}.{payload_b64}'.encode()

    private_key_pem = sa_json['private_key'].encode()
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    jwt_token = f'{header_b64}.{payload_b64}.{_b64url(signature)}'

    resp = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion':  jwt_token,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    access_token = data['access_token']
    expires_in   = int(data.get('expires_in', 3600))

    _token_cache[cache_key] = (access_token, time.time() + min(expires_in, 55 * 60))
    return access_token
