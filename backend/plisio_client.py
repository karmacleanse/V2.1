"""
Plisio crypto payment integration.
Creates hosted invoices (BTC, LTC, BCH, DOGE, USDT TRC/BEP, TRX, TON and more)
and verifies webhook signatures via HMAC-SHA1 of the PHP-serialized payload
(excluding `verify_hash`, with keys ksort'd) using the API secret key.

Reference (Plisio docs/PHP SDK):
    ksort($post)
    $postString = serialize($post)
    $checkKey = hash_hmac('sha1', $postString, $SECRET_KEY)
"""
import os
import hmac
import hashlib
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv
import httpx
import phpserialize

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
                         email: str = None,
                         custom_amount: float = None) -> dict:
    """
    Create a Plisio invoice with hosted checkout.
    Returns: {url, txn_id, order_id, amount_usd}
    
    If `custom_amount` is provided, it overrides the tier-based price.
    Used for self-assessed karmic compensation (any amount).
    """
    if not PLISIO_API_KEY:
        raise ValueError("PLISIO_API_KEY not configured")

    if custom_amount is not None:
        if custom_amount < 0.50 or custom_amount > 1000:
            raise ValueError(f"Custom amount must be between $0.50 and $1000")
        amount = round(custom_amount, 2)
        tier_label = 'custom'
    else:
        if tier not in PLISIO_PRICING:
            raise ValueError(f"Invalid tier: {tier}")
        amount = PLISIO_PRICING[tier]
        tier_label = tier
    
    # Unique order number per attempt (allows retry on same cert)
    order_number = f"{certificate_uuid}_{tier_label}_{uuid.uuid4().hex[:8]}"

    params = {
        'source_currency': 'USD',
        'source_amount': f"{amount:.2f}",
        'order_number': order_number,
        'order_name': f"Karma Cleanse \u2014 Premium Absolution (${amount:.2f})",
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


def _php_serialize(obj):
    """Serialize a dict/list/string to PHP's serialize() format.
    
    Plisio expects all values as strings (POST form data), then ksort'd,
    then PHP serialize, then HMAC-SHA1 with the secret key.
    """
    # phpserialize handles native types — convert dict keys/values to PHP-compatible
    # All keys are strings. All values should be passed as bytes/strings.
    if isinstance(obj, dict):
        # phpserialize requires bytes for strings; encode keys and values
        serializable = {}
        for k, v in obj.items():
            key = k.encode('utf-8') if isinstance(k, str) else k
            serializable[key] = _php_serialize_value(v)
        return phpserialize.dumps(serializable)
    return phpserialize.dumps(obj)


def _php_serialize_value(v):
    """Convert a Python value into a form suitable for phpserialize."""
    if v is None:
        return b''  # PHP empty string
    if isinstance(v, bool):
        return b'1' if v else b''
    if isinstance(v, (int, float)):
        # Plisio sends all values as POST strings — match that.
        return str(v).encode('utf-8')
    if isinstance(v, str):
        return v.encode('utf-8')
    if isinstance(v, bytes):
        return v
    if isinstance(v, list):
        return [_php_serialize_value(x) for x in v]
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            key = k.encode('utf-8') if isinstance(k, str) else k
            out[key] = _php_serialize_value(val)
        return out
    return str(v).encode('utf-8')


def verify_webhook_signature(payload: dict, received_hash: str) -> bool:
    """
    Verify Plisio webhook signature.
    Algorithm (from Plisio PHP SDK):
        1. Remove `verify_hash`
        2. ksort() the payload
        3. PHP serialize() the array (all values as strings)
        4. HMAC-SHA1 with secret key
    """
    if not PLISIO_API_KEY or not received_hash:
        return False
    try:
        payload_copy = {k: v for k, v in payload.items() if k != 'verify_hash'}
        # ksort — phpserialize.dumps with dict preserves insertion order, so we sort first
        sorted_payload = dict(sorted(payload_copy.items()))
        serialized = _php_serialize(sorted_payload)
        computed = hmac.new(
            PLISIO_API_KEY.encode('utf-8'),
            serialized,
            hashlib.sha1,
        ).hexdigest()
        if not hmac.compare_digest(computed, received_hash):
            logger.warning(
                f"Plisio sig mismatch. expected={received_hash} got={computed} "
                f"serialized_preview={serialized[:200]!r}"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Plisio signature error: {e}")
        return False


def normalize_status(plisio_status: str) -> str:
    """Map Plisio status to internal status.
    
    `mismatch` (underpaid/overpaid by amount outside dashboard tolerance) is
    treated as `paid_underpaid` — the agent should review manually but the
    money is on chain. Cert will NOT be auto-upgraded from this state.
    """
    mapping = {
        'new': 'pending',
        'pending': 'pending',
        'pending internal': 'pending',
        'expired': 'failed',
        'completed': 'paid',
        'mismatch': 'paid_underpaid',
        'error': 'failed',
        'cancelled': 'failed',
        'cancelled duplicate': 'failed',
    }
    return mapping.get(plisio_status, 'pending')
