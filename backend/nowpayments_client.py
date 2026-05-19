"""
NOWPayments crypto payment integration.
Creates hosted invoices (any of 300+ coins → settled in USDT TRC-20)
and verifies IPN webhook signatures via HMAC-SHA512.
"""
import os
import hmac
import hashlib
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

NOWPAYMENTS_API_KEY = os.environ.get('NOWPAYMENTS_API_KEY')
NOWPAYMENTS_IPN_SECRET = os.environ.get('NOWPAYMENTS_IPN_SECRET')
NOWPAYMENTS_BASE_URL = os.environ.get('NOWPAYMENTS_BASE_URL', 'https://api.nowpayments.io/v1')
NOWPAYMENTS_PAYOUT_CURRENCY = os.environ.get('NOWPAYMENTS_PAYOUT_CURRENCY', 'usdttrc20')

# Server-side pricing (NEVER trust frontend)
NOWPAYMENTS_PRICING = {
    'standard': 1.0,
    'premium': 3.0,
    'enterprise': 7.0,
}


async def create_invoice(tier: str, certificate_uuid: str, origin_url: str, backend_url: str) -> dict:
    """
    Create a NOWPayments hosted invoice.
    Returns: {invoice_url, invoice_id}
    """
    if tier not in NOWPAYMENTS_PRICING:
        raise ValueError(f"Invalid tier: {tier}")
    
    if not NOWPAYMENTS_API_KEY:
        raise ValueError("NOWPAYMENTS_API_KEY not configured")
    
    price_usd = NOWPAYMENTS_PRICING[tier]
    
    payload = {
        "price_amount": price_usd,
        "price_currency": "usd",
        "order_id": certificate_uuid,
        "order_description": f"Karma Cleanse Certificate ({tier})",
        "ipn_callback_url": f"{backend_url}/api/webhooks/nowpayments",
        "success_url": f"{origin_url}/?nowp_success=true&cert_uuid={certificate_uuid}",
        "cancel_url": f"{origin_url}/?nowp_cancel=true",
        "is_fee_paid_by_user": True,
    }
    
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NOWPAYMENTS_BASE_URL}/invoice",
            json=payload,
            headers=headers,
        )
        if resp.status_code >= 400:
            logger.error(f"NOWPayments invoice creation failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"Invoice creation failed: {resp.text}")
        
        data = resp.json()
        invoice_id = data.get("id") or data.get("invoice_id")
        invoice_url = data.get("invoice_url") or data.get("url")
        
        if not invoice_id or not invoice_url:
            raise RuntimeError(f"Invalid invoice response: {data}")
        
        # Add default pay currency so user lands on USDT TRC-20 (min ~$1, low fee)
        # instead of BTC which requires ~$50+ minimum
        separator = '&' if '?' in invoice_url else '?'
        invoice_url_with_currency = f"{invoice_url}{separator}payCurrency={NOWPAYMENTS_PAYOUT_CURRENCY}"
        
        return {
            "invoice_url": invoice_url_with_currency,
            "invoice_id": str(invoice_id),
            "amount_usd": price_usd,
        }


def verify_ipn_signature(raw_body: bytes, received_sig: str) -> bool:
    """
    Verify NOWPayments IPN signature.
    NOWPayments signs: sorted JSON keys serialization → HMAC-SHA512 with IPN secret.
    """
    if not NOWPAYMENTS_IPN_SECRET or not received_sig:
        return False
    
    try:
        # NOWPayments signs the sorted JSON keys of the parsed payload
        parsed = json.loads(raw_body)
        sorted_payload = json.dumps(parsed, sort_keys=True, separators=(',', ':'))
        
        computed = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode('utf-8'),
            sorted_payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed, received_sig)
    except Exception as e:
        logger.error(f"IPN signature verification error: {e}")
        return False


def normalize_payment_status(nowp_status: str) -> str:
    """Map NOWPayments payment_status to internal status"""
    mapping = {
        'waiting': 'pending',
        'confirming': 'pending',
        'confirmed': 'pending',
        'sending': 'pending',
        'partially_paid': 'pending',
        'finished': 'paid',
        'failed': 'failed',
        'refunded': 'failed',
        'expired': 'failed',
    }
    return mapping.get(nowp_status, 'pending')
