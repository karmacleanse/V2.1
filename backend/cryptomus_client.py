"""
Cryptomus crypto payment integration.
Creates hosted invoices (100+ coins → settled in USDT TRC-20)
and verifies webhook signatures via MD5(base64(payload) + API_KEY).
"""
import os
import hashlib
import json
import base64
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

CRYPTOMUS_API_KEY = os.environ.get('CRYPTOMUS_API_KEY')
CRYPTOMUS_MERCHANT_UUID = os.environ.get('CRYPTOMUS_MERCHANT_UUID')
CRYPTOMUS_BASE_URL = os.environ.get('CRYPTOMUS_BASE_URL', 'https://api.cryptomus.com/v1')

# Server-side pricing (NEVER trust frontend)
CRYPTOMUS_PRICING = {
    'standard': '1.00',
    'premium': '3.00',
    'enterprise': '7.00',
}


def _sign_payload(payload: dict) -> str:
    """Cryptomus signature: MD5(base64(json) + API_KEY)"""
    if not CRYPTOMUS_API_KEY:
        raise ValueError("CRYPTOMUS_API_KEY not configured")
    
    body = json.dumps(payload).encode('utf-8')
    body_b64 = base64.b64encode(body).decode('utf-8')
    sign = hashlib.md5((body_b64 + CRYPTOMUS_API_KEY).encode('utf-8')).hexdigest()
    return sign


async def create_payment(tier: str, certificate_uuid: str, origin_url: str, backend_url: str) -> dict:
    """
    Create a Cryptomus payment invoice.
    Returns: {url, uuid (cryptomus payment uuid), order_id}
    """
    if tier not in CRYPTOMUS_PRICING:
        raise ValueError(f"Invalid tier: {tier}")
    
    if not CRYPTOMUS_MERCHANT_UUID or CRYPTOMUS_MERCHANT_UUID == 'placeholder_get_from_dashboard':
        raise ValueError("CRYPTOMUS_MERCHANT_UUID not configured")
    
    amount = CRYPTOMUS_PRICING[tier]
    # Unique order ID = certificate_uuid + tier (allows retry for same cert)
    order_id = f"{certificate_uuid}_{tier}_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "amount": amount,
        "currency": "USD",
        "order_id": order_id,
        "url_return": f"{origin_url}/?cryptomus_cancel=true",
        "url_success": f"{origin_url}/?cryptomus_success=true&cert_uuid={certificate_uuid}",
        "url_callback": f"{backend_url}/api/webhooks/cryptomus",
        "is_payment_multiple": False,
        "lifetime": 3600,  # 1 hour
        "additional_data": json.dumps({
            "certificate_uuid": certificate_uuid,
            "tier": tier,
        }),
    }
    
    sign = _sign_payload(payload)
    headers = {
        "merchant": CRYPTOMUS_MERCHANT_UUID,
        "sign": sign,
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{CRYPTOMUS_BASE_URL}/payment",
            json=payload,
            headers=headers,
        )
        
        if resp.status_code >= 400:
            logger.error(f"Cryptomus payment creation failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"Payment creation failed: {resp.text}")
        
        data = resp.json()
        result = data.get("result", {})
        
        payment_url = result.get("url")
        payment_uuid = result.get("uuid")
        
        if not payment_url or not payment_uuid:
            raise RuntimeError(f"Invalid Cryptomus response: {data}")
        
        return {
            "url": payment_url,
            "uuid": payment_uuid,
            "order_id": order_id,
            "amount_usd": float(amount),
        }


def verify_webhook_signature(payload: dict, received_sign: str) -> bool:
    """
    Verify Cryptomus webhook signature.
    Cryptomus signs: MD5(base64(payload_without_sign) + API_KEY)
    """
    if not CRYPTOMUS_API_KEY or not received_sign:
        return False
    
    try:
        # Remove 'sign' field from payload for verification
        payload_copy = {k: v for k, v in payload.items() if k != 'sign'}
        body = json.dumps(payload_copy).encode('utf-8')
        body_b64 = base64.b64encode(body).decode('utf-8')
        computed = hashlib.md5((body_b64 + CRYPTOMUS_API_KEY).encode('utf-8')).hexdigest()
        
        return computed == received_sign
    except Exception as e:
        logger.error(f"Cryptomus signature error: {e}")
        return False


def normalize_status(cryptomus_status: str) -> str:
    """Map Cryptomus status to internal status"""
    mapping = {
        'paid': 'paid',
        'paid_over': 'paid',
        'process': 'pending',
        'check': 'pending',
        'confirm_check': 'pending',
        'wrong_amount': 'failed',
        'wrong_amount_waiting': 'pending',
        'cancel': 'failed',
        'fail': 'failed',
        'system_fail': 'failed',
        'refund_process': 'pending',
        'refund_fail': 'failed',
        'refund_paid': 'failed',
        'locked': 'pending',
    }
    return mapping.get(cryptomus_status, 'pending')
