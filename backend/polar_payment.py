"""
Polar.sh payment integration.
Creates checkout sessions and verifies orders via webhooks.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from polar_sdk import Polar
from polar_sdk.webhooks import validate_event, WebhookVerificationError

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

POLAR_ACCESS_TOKEN = os.environ.get('POLAR_ACCESS_TOKEN')
POLAR_SERVER = os.environ.get('POLAR_SERVER', 'production')
POLAR_WEBHOOK_SECRET = os.environ.get('POLAR_WEBHOOK_SECRET')

# Server-side mapping of tier -> product ID (NEVER trust frontend)
POLAR_PRODUCTS = {
    'standard': os.environ.get('POLAR_PRODUCT_STANDARD'),
    'premium': os.environ.get('POLAR_PRODUCT_PREMIUM'),
    'enterprise': os.environ.get('POLAR_PRODUCT_ENTERPRISE'),
}

# Pricing (for display/validation; actual amount enforced by Polar product)
POLAR_PRICING = {
    'standard': 1.00,
    'premium': 3.00,
    'enterprise': 7.00,
}


def get_polar_client() -> Polar:
    """Initialize Polar SDK client"""
    if not POLAR_ACCESS_TOKEN:
        raise ValueError("POLAR_ACCESS_TOKEN not configured")
    return Polar(access_token=POLAR_ACCESS_TOKEN, server=POLAR_SERVER)


async def create_polar_checkout(tier: str, certificate_uuid: str, origin_url: str) -> dict:
    """
    Create a Polar checkout session for the given tier.
    Returns: {url, checkout_id}
    """
    if tier not in POLAR_PRODUCTS:
        raise ValueError(f"Invalid tier: {tier}")
    
    product_id = POLAR_PRODUCTS[tier]
    if not product_id:
        raise ValueError(f"Product ID not configured for tier: {tier}")
    
    polar = get_polar_client()
    
    success_url = f"{origin_url}/?polar_success=true&checkout_id={{CHECKOUT_ID}}"
    
    try:
        checkout = polar.checkouts.create(request={
            "products": [product_id],
            "success_url": success_url,
            "metadata": {
                "certificate_uuid": certificate_uuid,
                "tier": tier,
            },
        })
        
        logger.info(f"Created Polar checkout {checkout.id} for cert {certificate_uuid}")
        return {
            'url': checkout.url,
            'checkout_id': checkout.id,
        }
    except Exception as e:
        logger.error(f"Polar checkout creation failed: {e}")
        raise


def verify_polar_webhook(raw_body: bytes, headers: dict) -> dict:
    """
    Validate webhook signature and return parsed event.
    Raises WebhookVerificationError on invalid signature.
    """
    if not POLAR_WEBHOOK_SECRET or POLAR_WEBHOOK_SECRET == 'placeholder_set_after_dashboard_setup':
        # In dev/initial setup, allow events through (but log warning)
        logger.warning("POLAR_WEBHOOK_SECRET not set — skipping signature verification (UNSAFE)")
        import json
        return json.loads(raw_body)
    
    return validate_event(raw_body, headers, POLAR_WEBHOOK_SECRET)


async def get_polar_order(order_id: str) -> dict:
    """Fetch order details from Polar API"""
    polar = get_polar_client()
    order = polar.orders.get(id=order_id)
    return order
