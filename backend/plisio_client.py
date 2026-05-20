"""
Plisio crypto payment integration.
Creates hosted invoices (BTC, LTC, BCH, DOGE, USDT TRC/BEP, TRX, TON and more)
and verifies webhook signatures via HMAC-SHA256 of the JSON payload
(excluding `verify_hash`) using the API secret key.

Plisio API specifics:
- All requests are GET with query parameters.
- Base URL: https://api.plisio.net/api/v1
- Webhook signature field: `verify_hash` in body, computed as
  hmac_sha256(secret_key, json(payload_without_verify_hash_sorted))
"""
import os
import hmac
import hashlib
import json
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

PLISIO_API_KEY = os.environ.get('PLISIO_API_KEY')
PLISIO_API_URL = os.environ.get('PLISIO_API_URL', 'https://api.plisio.net/api/v1')

# Server-side pricing (NEVER trust frontend)
PLISIO_PRICING = {
    'standard': 1.00,
    'premium': 3.00,
    'enterprise': 7.00,
}


async def create_invoice(tier: str, certificate_uuid: str,
                         origin_url: str, backend_url: str,
                         email: str = None) -> dict:
    """
    Create a Plisio invoice with hosted checkout.
    Returns: {url, txn_id, order_id, amount_usd}
    """
    if tier not in PLISIO_PRICING:
        raise ValueError(f"Invalid tier: {tier}")
    if not PLISIO_API_KEY:
        raise ValueError("PLISIO_API_KEY not configured")

    amount = PLISIO_PRICING[tier]
    # Unique order number per attempt (allows retry on same cert)
    order_number = f"{certificate_uuid}_{tier}_{uuid.uuid4().hex[:8]}"

    params = {
        'source_currency': 'USD',
        'source_amount': f"{amount:.2f}",
        'order_number': order_number,
        'order_name': f"Karma Cleanse — {tier.capitalize()} Protocol",
        'callback_url': f"{backend_url}/api/webhooks/plisio?json=true",
        'success_callback_url': f"{origin_url}/?plisio_success=true&cert_uuid={certificate_uuid}",
        'fail_callback_url': f"{origin_url}/?plisio_cancel=true",
        'api_key': PLISIO_API_KEY,
    }
    if email:
        params['email'] = email

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{PLISIO_API_URL}/invoices/new", params=params)

        if resp.status_code >= 400:
            logger.error(f"Plisio invoice creation HTTP {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Invoice creation failed: {resp.text}")

        data = resp.json()
        if data.get('status') != 'success':
            logger.error(f"Plisio invoice creation failed: {data}")
            raise RuntimeError(f"Plisio error: {data.get('data', {}).get('message', 'unknown')}")

        result = data.get('data', {})
        invoice_url = result.get('invoice_url')
        txn_id = result.get('txn_id')

        if not invoice_url or not txn_id:
            raise RuntimeError(f"Invalid Plisio response: {data}")

        return {
            'url': invoice_url,
            'txn_id': txn_id,
            'order_id': order_number,
            'amount_usd': amount,
        }


async def get_invoice_status(txn_id: str) -> dict:
    """Fetch invoice status by Plisio transaction id."""
    if not PLISIO_API_KEY:
        raise ValueError("PLISIO_API_KEY not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{PLISIO_API_URL}/operations/{txn_id}",
            params={'api_key': PLISIO_API_KEY},
        )
        resp.raise_for_status()
        return resp.json()


def verify_webhook_signature(payload: dict, received_hash: str) -> bool:
    """
    Verify Plisio webhook signature.
    Algorithm: HMAC-SHA256 of JSON-encoded payload (with keys sorted)
    excluding the `verify_hash` field, using the API secret key.
    """
    if not PLISIO_API_KEY or not received_hash:
        return False
    try:
        payload_copy = {k: v for k, v in payload.items() if k != 'verify_hash'}
        # Plisio expects ksort + json_encode (PHP); Python equivalent:
        body = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))
        computed = hmac.new(
            PLISIO_API_KEY.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, received_hash)
    except Exception as e:
        logger.error(f"Plisio signature error: {e}")
        return False


def normalize_status(plisio_status: str) -> str:
    """Map Plisio status to internal status."""
    mapping = {
        'new': 'pending',
        'pending': 'pending',
        'pending internal': 'pending',
        'expired': 'failed',
        'completed': 'paid',
        'mismatch': 'pending',  # underpaid / overpaid — manual review
        'error': 'failed',
        'cancelled': 'failed',
    }
    return mapping.get(plisio_status, 'pending')
