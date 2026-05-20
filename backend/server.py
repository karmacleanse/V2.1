from fastapi import FastAPI, APIRouter, HTTPException, Request, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
import resend
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid as uuid_lib

from models import (
    Certificate, CertificateCreate, AnalyzeRequest, 
    CheckoutRequest, DeliveryRequest, PaymentTransaction
)
from severity_analyzer import analyze_severity
from registry_id_generator import generate_registry_id
from polar_payment import (
    create_polar_checkout, verify_polar_webhook, POLAR_PRODUCTS, POLAR_PRICING
)
from nowpayments_client import (
    create_invoice as nowp_create_invoice,
    verify_ipn_signature as nowp_verify_signature,
    normalize_payment_status as nowp_normalize_status,
    NOWPAYMENTS_PRICING,
)
from cryptomus_client import (
    create_payment as cryptomus_create_payment,
    verify_webhook_signature as cryptomus_verify_signature,
    normalize_status as cryptomus_normalize_status,
    CRYPTOMUS_PRICING,
)
from sketch_generator import generate_sketch
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# Resend
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
resend.api_key = RESEND_API_KEY

# Base URL
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:3000')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pricing tiers (DO NOT accept from frontend)
PRICING_TIERS = {
    'standard': 1.00,
    'premium': 3.00,
    'enterprise': 7.00,
}


@api_router.get("/")
async def root():
    return {"message": "Karma Cleanse API v2.1"}


@api_router.post("/analyze")
async def analyze_confession(request: AnalyzeRequest):
    """Analyze confession and return severity classification"""
    if not request.confession or len(request.confession.strip()) < 5:
        raise HTTPException(status_code=400, detail="Confession too short")
    
    result = analyze_severity(request.confession)
    return result


@api_router.post("/certificate")
async def create_certificate(cert_data: CertificateCreate):
    """Create a new certificate (temporary/free by default)"""
    cert_uuid = str(uuid_lib.uuid4())
    registry_id = generate_registry_id()
    
    certificate = {
        'uuid': cert_uuid,
        'registry_id': registry_id,
        'name': cert_data.name,
        'confession': cert_data.confession,
        'severity_class': cert_data.severity_class,
        'stability': cert_data.stability,
        'risk_score': cert_data.risk_score,
        'protocol': cert_data.protocol,
        'diagnostics': cert_data.diagnostics,
        'status': 'temporary',  # default
        'tier': 'free',  # default
        'payment_amount': 0.0,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    
    await db.certificates.insert_one(certificate)
    
    return {
        'uuid': cert_uuid,
        'registry_id': registry_id,
        'status': 'temporary',
        'tier': 'free',
    }


@api_router.get("/certificate/{cert_uuid}")
async def get_certificate(cert_uuid: str):
    """Get certificate by UUID (public verification)"""
    cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return cert


@api_router.get("/verify/{registry_id}")
async def verify_certificate(registry_id: str):
    """Verify certificate by registry ID (public)"""
    cert = await db.certificates.find_one({'registry_id': registry_id}, {'_id': 0, 'confession': 0})
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found in registry")
    
    return cert


@api_router.post("/checkout/session")
async def create_checkout_session(request: CheckoutRequest):
    """Create Stripe checkout session for certificate upgrade"""
    
    # Validate tier
    if request.tier not in PRICING_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    # Get amount from server-side pricing (NEVER from frontend)
    amount = PRICING_TIERS[request.tier]
    
    # Verify certificate exists
    cert = await db.certificates.find_one({'uuid': request.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Initialize Stripe checkout
    webhook_url = f"{request.origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Build URLs from origin
    success_url = f"{request.origin_url}/?success=true&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{request.origin_url}/?canceled=true"
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'certificate_uuid': request.certificate_uuid,
            'tier': request.tier,
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction = {
        'session_id': session.session_id,
        'certificate_uuid': request.certificate_uuid,
        'amount': amount,
        'currency': 'usd',
        'status': 'pending',
        'payment_status': 'unpaid',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_transactions.insert_one(transaction)
    
    logger.info(f"Created checkout session {session.session_id} for certificate {request.certificate_uuid}")
    
    return {'url': session.url, 'session_id': session.session_id}


@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request):
    """Poll payment status"""
    
    # Get transaction from DB
    transaction = await db.payment_transactions.find_one({'session_id': session_id}, {'_id': 0})
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already processed, return cached status
    if transaction['payment_status'] == 'paid':
        return {
            'status': 'complete',
            'payment_status': 'paid',
            'certificate_uuid': transaction['certificate_uuid'],
        }
    
    # Otherwise, check with Stripe
    origin_url = str(request.base_url).rstrip('/')
    webhook_url = f"{origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction
        await db.payment_transactions.update_one(
            {'session_id': session_id},
            {'$set': {
                'status': checkout_status.status,
                'payment_status': checkout_status.payment_status,
            }}
        )
        
        # If payment successful, upgrade certificate
        if checkout_status.payment_status == 'paid':
            cert_uuid = transaction['certificate_uuid']
            
            # Check if already upgraded (prevent double processing)
            cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
            if cert and cert['tier'] == 'free':
                await db.certificates.update_one(
                    {'uuid': cert_uuid},
                    {'$set': {
                        'tier': 'paid',
                        'status': 'certified',
                        'payment_amount': checkout_status.amount_total / 100.0,  # convert cents to dollars
                    }}
                )
                logger.info(f"Upgraded certificate {cert_uuid} to paid tier")
        
        return {
            'status': checkout_status.status,
            'payment_status': checkout_status.payment_status,
            'certificate_uuid': transaction['certificate_uuid'],
        }
        
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    """Handle Stripe webhook events"""
    
    body = await request.body()
    origin_url = str(request.base_url).rstrip('/')
    webhook_url = f"{origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        logger.info(f"Webhook event: {webhook_response.event_type}, session: {webhook_response.session_id}")
        
        # Update transaction
        if webhook_response.session_id:
            await db.payment_transactions.update_one(
                {'session_id': webhook_response.session_id},
                {'$set': {
                    'payment_status': webhook_response.payment_status,
                }}
            )
            
            # Upgrade certificate if paid
            if webhook_response.payment_status == 'paid' and webhook_response.metadata:
                cert_uuid = webhook_response.metadata.get('certificate_uuid')
                if cert_uuid:
                    cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
                    if cert and cert['tier'] == 'free':
                        await db.certificates.update_one(
                            {'uuid': cert_uuid},
                            {'$set': {
                                'tier': 'paid',
                                'status': 'certified',
                            }}
                        )
                        logger.info(f"Certificate {cert_uuid} upgraded via webhook")
        
        return {'received': True}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@api_router.post("/polar/checkout")
async def polar_checkout_endpoint(request: CheckoutRequest):
    """Create Polar.sh checkout session for paid tier"""
    if request.tier not in POLAR_PRODUCTS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    # Verify certificate exists
    cert = await db.certificates.find_one({'uuid': request.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    try:
        result = await create_polar_checkout(
            tier=request.tier,
            certificate_uuid=request.certificate_uuid,
            origin_url=request.origin_url,
        )
        
        # Record transaction
        transaction = {
            'session_id': result['checkout_id'],
            'certificate_uuid': request.certificate_uuid,
            'amount': POLAR_PRICING[request.tier],
            'currency': 'usd',
            'tier': request.tier,
            'payment_method': 'polar_card',
            'status': 'pending',
            'payment_status': 'unpaid',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(transaction)
        
        return {'url': result['url'], 'session_id': result['checkout_id']}
        
    except Exception as e:
        logger.error(f"Polar checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout creation failed: {str(e)}")


@api_router.get("/polar/status/{checkout_id}")
async def polar_status(checkout_id: str):
    """Check Polar payment status (used after redirect from Polar checkout)"""
    transaction = await db.payment_transactions.find_one({'session_id': checkout_id}, {'_id': 0})
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        'status': transaction.get('status', 'pending'),
        'payment_status': transaction.get('payment_status', 'unpaid'),
        'certificate_uuid': transaction['certificate_uuid'],
    }


@api_router.post("/webhooks/polar")
async def polar_webhook(request: Request):
    """Handle Polar webhook events (order.paid, etc.)"""
    raw_body = await request.body()
    headers = dict(request.headers)
    
    try:
        event = verify_polar_webhook(raw_body, headers)
    except Exception as e:
        logger.error(f"Polar webhook verification failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
    data = event.get('data') if isinstance(event, dict) else getattr(event, 'data', None)
    
    if hasattr(data, 'model_dump'):
        data = data.model_dump()
    
    logger.info(f"Polar webhook: {event_type}")
    
    # Idempotency: prevent duplicate processing
    webhook_id = headers.get('webhook-id')
    if webhook_id:
        existing = await db.processed_webhooks.find_one({'_id': webhook_id})
        if existing:
            logger.info(f"Webhook {webhook_id} already processed")
            return {'received': True, 'duplicate': True}
        await db.processed_webhooks.insert_one({
            '_id': webhook_id,
            'event_type': event_type,
            'processed_at': datetime.now(timezone.utc).isoformat(),
        })
    
    # Handle order.paid
    if event_type == 'order.paid' or event_type == 'order.created':
        metadata = data.get('metadata', {}) if data else {}
        cert_uuid = metadata.get('certificate_uuid')
        checkout_id = data.get('checkout_id') if data else None
        order_id = data.get('id') if data else None
        amount = (data.get('amount', 0) / 100.0) if data else 0  # Polar uses cents
        
        if cert_uuid:
            cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
            if cert and cert['tier'] == 'free':
                await db.certificates.update_one(
                    {'uuid': cert_uuid},
                    {'$set': {
                        'tier': 'paid',
                        'status': 'certified',
                        'payment_amount': amount,
                        'payment_method': 'polar_card',
                    }}
                )
                logger.info(f"Certificate {cert_uuid} upgraded via Polar webhook")
            
            # Update transaction
            if checkout_id:
                await db.payment_transactions.update_one(
                    {'session_id': checkout_id},
                    {'$set': {
                        'status': 'complete',
                        'payment_status': 'paid',
                        'polar_order_id': order_id,
                    }}
                )
    
    return {'received': True}


@api_router.post("/nowpayments/invoice")
async def nowpayments_invoice_endpoint(request: CheckoutRequest):
    """Create NOWPayments invoice for paid tier (accepts 300+ cryptos)"""
    if request.tier not in NOWPAYMENTS_PRICING:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    cert = await db.certificates.find_one({'uuid': request.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    try:
        result = await nowp_create_invoice(
            tier=request.tier,
            certificate_uuid=request.certificate_uuid,
            origin_url=request.origin_url,
            backend_url=BASE_URL,
        )
        
        # Record transaction
        transaction = {
            'session_id': result['invoice_id'],
            'invoice_id': result['invoice_id'],
            'certificate_uuid': request.certificate_uuid,
            'amount': result['amount_usd'],
            'currency': 'usd',
            'tier': request.tier,
            'payment_method': 'nowpayments',
            'status': 'pending',
            'payment_status': 'unpaid',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(transaction)
        
        logger.info(f"NOWPayments invoice {result['invoice_id']} for cert {request.certificate_uuid}")
        return {'url': result['invoice_url'], 'invoice_id': result['invoice_id']}
        
    except Exception as e:
        logger.error(f"NOWPayments invoice error: {e}")
        raise HTTPException(status_code=500, detail=f"Invoice creation failed: {str(e)}")


@api_router.get("/nowpayments/status/{certificate_uuid}")
async def nowpayments_status(certificate_uuid: str):
    """Check NOWPayments payment status by certificate uuid"""
    cert = await db.certificates.find_one({'uuid': certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return {
        'tier': cert.get('tier', 'free'),
        'status': cert.get('status', 'temporary'),
        'is_paid': cert.get('tier') == 'paid',
    }


@api_router.post("/webhooks/nowpayments")
async def nowpayments_webhook(request: Request):
    """Handle NOWPayments IPN callbacks (signature verified via HMAC-SHA512)"""
    raw_body = await request.body()
    received_sig = request.headers.get('x-nowpayments-sig')
    
    if not received_sig:
        logger.warning("NOWPayments webhook missing signature")
        raise HTTPException(status_code=400, detail="Missing signature")
    
    if not nowp_verify_signature(raw_body, received_sig):
        logger.error("NOWPayments webhook invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    order_id = payload.get('order_id')  # = certificate_uuid
    payment_status = payload.get('payment_status', '')
    payment_id = payload.get('payment_id')
    invoice_id = payload.get('invoice_id')
    pay_amount = payload.get('pay_amount', 0)
    pay_currency = payload.get('pay_currency', 'usdt')
    
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id")
    
    logger.info(f"NOWPayments IPN: status={payment_status}, order={order_id}, payment_id={payment_id}")
    
    normalized = nowp_normalize_status(payment_status)
    
    # Update transaction
    await db.payment_transactions.update_one(
        {'certificate_uuid': order_id, 'payment_method': 'nowpayments'},
        {'$set': {
            'payment_status': normalized,
            'nowp_payment_id': str(payment_id) if payment_id else None,
            'nowp_payment_status': payment_status,
            'pay_amount': pay_amount,
            'pay_currency': pay_currency,
        }}
    )
    
    # Upgrade certificate if paid
    if normalized == 'paid':
        cert = await db.certificates.find_one({'uuid': order_id}, {'_id': 0})
        if cert and cert.get('tier') == 'free':
            await db.certificates.update_one(
                {'uuid': order_id},
                {'$set': {
                    'tier': 'paid',
                    'status': 'certified',
                    'payment_amount': NOWPAYMENTS_PRICING.get(cert.get('tier_requested', 'standard'), 1.0),
                    'payment_method': f'nowpayments_{pay_currency}',
                }}
            )
            logger.info(f"Certificate {order_id} upgraded via NOWPayments ({pay_currency})")
    
    return {'received': True}



@api_router.post("/cryptomus/payment")
async def cryptomus_payment_endpoint(request: CheckoutRequest):
    """Create Cryptomus payment invoice (100+ coins, min $0.50)"""
    if request.tier not in CRYPTOMUS_PRICING:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    cert = await db.certificates.find_one({'uuid': request.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    try:
        result = await cryptomus_create_payment(
            tier=request.tier,
            certificate_uuid=request.certificate_uuid,
            origin_url=request.origin_url,
            backend_url=BASE_URL,
        )
        
        transaction = {
            'session_id': result['uuid'],
            'cryptomus_uuid': result['uuid'],
            'order_id': result['order_id'],
            'certificate_uuid': request.certificate_uuid,
            'amount': result['amount_usd'],
            'currency': 'usd',
            'tier': request.tier,
            'payment_method': 'cryptomus',
            'status': 'pending',
            'payment_status': 'unpaid',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(transaction)
        
        logger.info(f"Cryptomus payment {result['uuid']} for cert {request.certificate_uuid}")
        return {'url': result['url'], 'uuid': result['uuid']}
        
    except Exception as e:
        logger.error(f"Cryptomus payment error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@api_router.get("/cryptomus/status/{certificate_uuid}")
async def cryptomus_status(certificate_uuid: str):
    """Check Cryptomus payment status by certificate uuid"""
    cert = await db.certificates.find_one({'uuid': certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return {
        'tier': cert.get('tier', 'free'),
        'status': cert.get('status', 'temporary'),
        'is_paid': cert.get('tier') == 'paid',
    }


@api_router.post("/webhooks/cryptomus")
async def cryptomus_webhook(request: Request):
    """Handle Cryptomus webhook (signature verified via MD5)"""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    received_sign = payload.get('sign')
    if not received_sign:
        logger.warning("Cryptomus webhook missing signature")
        raise HTTPException(status_code=400, detail="Missing signature")
    
    if not cryptomus_verify_signature(payload, received_sign):
        logger.error("Cryptomus webhook invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    status = payload.get('status', '')
    order_id = payload.get('order_id', '')
    amount = payload.get('amount', '0')
    payer_currency = payload.get('payer_currency', 'usdt')
    
    logger.info(f"Cryptomus webhook: status={status}, order={order_id}")
    
    cert_uuid = order_id.split('_')[0] if order_id else None
    if not cert_uuid:
        raise HTTPException(status_code=400, detail="Invalid order_id")
    
    normalized = cryptomus_normalize_status(status)
    
    await db.payment_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'payment_status': normalized,
            'cryptomus_status': status,
            'paid_amount': amount,
            'paid_currency': payer_currency,
        }}
    )
    
    if normalized == 'paid':
        cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
        if cert and cert.get('tier') == 'free':
            await db.certificates.update_one(
                {'uuid': cert_uuid},
                {'$set': {
                    'tier': 'paid',
                    'status': 'certified',
                    'payment_amount': float(amount),
                    'payment_method': f'cryptomus_{payer_currency}',
                }}
            )
            logger.info(f"Certificate {cert_uuid} upgraded via Cryptomus ({payer_currency})")
    
    return {'received': True}


@api_router.post("/sketch/generate/{cert_uuid}")
async def generate_sketch_endpoint(cert_uuid: str):
    """
    Generate AI sketch for a paid certificate (idempotent).
    Returns existing sketch_url if already generated.
    """
    cert = await db.certificates.find_one({'uuid': cert_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Only paid certificates get sketches
    if cert.get('tier') != 'paid':
        return {'sketch_url': None, 'reason': 'Free tier - no sketch'}
    
    # If already generated, return cached
    if cert.get('sketch_url'):
        return {'sketch_url': cert['sketch_url'], 'cached': True}
    
    # Generate
    result = await generate_sketch(
        severity_class=cert.get('severity_class', 'Moderate'),
        confession=cert.get('confession', ''),
    )
    
    if result.get('error'):
        logger.error(f"Sketch gen failed for {cert_uuid}: {result['error']}")
        return {'sketch_url': None, 'error': result['error']}
    
    # Save to DB
    await db.certificates.update_one(
        {'uuid': cert_uuid},
        {'$set': {
            'sketch_url': result['url'],
            'sketch_prompt': result.get('prompt'),
            'sketch_seed': result.get('seed'),
        }}
    )
    
    return {'sketch_url': result['url'], 'cached': False}


@api_router.post("/delivery/schedule")
async def schedule_delivery(delivery: DeliveryRequest):
    """Schedule email delivery of certificate"""
    
    # Verify certificate exists
    cert = await db.certificates.find_one({'uuid': delivery.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Calculate send time
    send_at = datetime.now(timezone.utc) + timedelta(hours=delivery.delay_hours)
    
    # Create scheduled delivery record
    scheduled = {
        'certificate_uuid': delivery.certificate_uuid,
        'recipient_email': delivery.recipient_email,
        'message': delivery.message,
        'send_at': send_at.isoformat(),
        'sent': False,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    
    result = await db.scheduled_deliveries.insert_one(scheduled)
    
    logger.info(f"Scheduled delivery for {delivery.recipient_email} at {send_at}")
    
    return {
        'scheduled': True,
        'send_at': send_at.isoformat(),
        'recipient': delivery.recipient_email,
    }


@api_router.post("/delivery/send-now")
async def send_certificate_email(certificate_uuid: str, recipient_email: str, message: Optional[str] = None):
    """Send certificate email immediately (for testing or instant delivery)"""
    
    # Get certificate
    cert = await db.certificates.find_one({'uuid': certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Build verification URL
    verification_url = f"{BASE_URL}/verify/{cert['registry_id']}"
    
    # Create HTML email
    message_html = f'<div class="field"><div class="label">Message</div><div class="value">{message}</div></div>' if message else ''
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'IBM Plex Mono', monospace; background: #F4F4F0; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border: 2px solid #0A0A0A; padding: 40px; }}
            .header {{ text-transform: uppercase; font-weight: 900; font-size: 24px; margin-bottom: 20px; }}
            .registry-id {{ font-size: 18px; font-weight: bold; color: #D92D20; margin: 20px 0; }}
            .field {{ margin: 10px 0; font-size: 14px; }}
            .label {{ text-transform: uppercase; font-weight: bold; font-size: 11px; letter-spacing: 0.1em; }}
            .value {{ font-size: 13px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #0A0A0A; font-size: 11px; color: #737373; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">Karma Cleanse Certificate</div>
            <div class="registry-id">Registry ID: {cert['registry_id']}</div>
            
            <div class="field">
                <div class="label">Subject</div>
                <div class="value">{cert.get('name', 'Anonymous Entity')}</div>
            </div>
            
            <div class="field">
                <div class="label">Severity Classification</div>
                <div class="value">{cert['severity_class']}</div>
            </div>
            
            <div class="field">
                <div class="label">Emotional Stability</div>
                <div class="value">{cert['stability']}</div>
            </div>
            
            <div class="field">
                <div class="label">Risk Score</div>
                <div class="value">{cert['risk_score']}/100</div>
            </div>
            
            <div class="field">
                <div class="label">Protocol</div>
                <div class="value">{cert['protocol']}</div>
            </div>
            
            <div class="field">
                <div class="label">Status</div>
                <div class="value">{cert['status'].upper()} - {cert['tier'].upper()} TIER</div>
            </div>
            
            {message_html}
            
            <div class="footer">
                Verify this certificate: <a href="{verification_url}">{verification_url}</a><br>
                This is an official Karma Cleanse document. Emotional bureaucracy since 2026.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send email via Resend
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": f"Karma Cleanse Certificate \u2014 {cert['registry_id']}",
            "html": html_content
        }
        
        email_result = await asyncio.to_thread(resend.Emails.send, params)
        
        logger.info(f"Email sent to {recipient_email}, email_id: {email_result.get('id')}")
        
        return {
            'sent': True,
            'recipient': recipient_email,
            'email_id': email_result.get('id'),
        }
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
