"""Cyzora Pay client (M-Pesa STK push) and webhook signature check.

The secret key and webhook secret come from config (environment variables) and never leave the server.
Amounts are integer cents in whole shillings (KES 1,500 = 150000).

NOT VERIFIED AGAINST THE LIVE DOCS: this was written from the integration brief because docs.cyzora.co.ke
was unreachable. The brief fixes the endpoints, headers, statuses, event names and signature scheme, but not
the JSON shape of a charge object. `charge_fields` is the single place that reads it. If a field name differs,
payments fail safe (an invoice stays unpaid) and only that function needs to change.
"""
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app

MAX_TRIES = 3


class CyzoraError(Exception):
    """The provider refused or could not be reached. `status` is the HTTP status, or None if unreachable."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def configured():
    return bool(current_app.config.get("CYZORA_SECRET_KEY"))


def key_is_live():
    return (current_app.config.get("CYZORA_SECRET_KEY") or "").startswith("sk_live_")


def _request(method, path, body=None, idempotency_key=None):
    key = current_app.config.get("CYZORA_SECRET_KEY")
    if not key:
        raise CyzoraError("Online payments are not configured yet")
    headers = {"X-API-Key": key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    url = current_app.config["CYZORA_BASE_URL"].rstrip("/") + path
    delay = current_app.config["CYZORA_RETRY_DELAY"]
    for attempt in range(MAX_TRIES):
        req = urllib.request.Request(url, method=method, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=current_app.config["CYZORA_TIMEOUT"]) as res:
                payload = json.loads(res.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                message = json.loads(e.read().decode()).get("error")
            except (ValueError, AttributeError):
                message = None
            last = attempt == MAX_TRIES - 1
            # 429: back off and retry. 409 with an Idempotency-Key: the same request may still be in flight.
            if not last and (e.code == 429 or (e.code == 409 and idempotency_key)):
                time.sleep(delay * 2 ** attempt)
                continue
            raise CyzoraError(message or f"Payment provider returned HTTP {e.code}", e.code) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            current_app.logger.warning("Cyzora request failed: %s", e)
            raise CyzoraError("Could not reach the payment provider") from e
        except ValueError as e:
            raise CyzoraError("Payment provider sent an unreadable response") from e
        if not isinstance(payload, dict):
            raise CyzoraError("Payment provider sent an unexpected response")
        return payload
    raise CyzoraError("Payment provider is busy, please try again", 429)  # pragma: no cover


def create_charge(amount_cents, phone, account_ref, metadata, idempotency_key):
    """STK push. `phone` is 2547XXXXXXXX. Every metadata value must be text."""
    return _request("POST", "/charges", {
        "amount": int(amount_cents), "phone": phone, "account_ref": account_ref,
        "metadata": {k: str(v) for k, v in metadata.items()}}, idempotency_key=idempotency_key)


def get_charge(charge_id):
    return _request("GET", "/charges/" + urllib.parse.quote(str(charge_id), safe=""))


def charge_fields(obj):
    """The only place that reads a charge object (from POST/GET /charges or a webhook event)."""
    data = obj.get("data") if isinstance(obj.get("data"), dict) else obj
    cents = data.get("amount_cents", data.get("amount"))
    return {"id": data.get("id"), "status": data.get("status"),
            "amount_cents": cents if isinstance(cents, (int, float)) and not isinstance(cents, bool) else None,
            "receipt": data.get("receipt")}


def verify_signature(raw_body, header, secret):
    """X-Cyzora-Signature is the hex HMAC-SHA256 of the RAW body. Constant-time compare."""
    if not secret or not header or not isinstance(raw_body, bytes):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.strip().lower())
