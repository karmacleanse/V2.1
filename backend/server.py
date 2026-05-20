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
from pydantic import BaseModel, EmailStr

from models import (
    Certificate, CertificateCreate, AnalyzeRequest, 
    CheckoutRequest, DeliveryRequest, PaymentTransaction
)
from severity_analyzer import analyze_severity
from registry_id_generator import generate_registry_id, generate_compliance_id
from polar_payment import (
    create_polar_checkout, verify_polar_webhook, POLAR_PRODUCTS, POLAR_PRICING
)
from plisio_client import (
    create_invoice as plisio_create_invoice,
    verify_webhook_signature as plisio_verify_signature,
    normalize_status as plisio_normalize_status,
    PLISIO_PRICING,
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


class ComplianceReceiptRequest(BaseModel):
    name: Optional[str] = None  # optional — Anonymous Acknowledger if blank
    acknowledgments: Optional[list] = None  # which sections were acknowledged
    jurisdiction: Optional[str] = None  # user-stated jurisdiction (free text)


@api_router.post("/compliance-receipt")
async def create_compliance_receipt(request: ComplianceReceiptRequest):
    """Issue a satirical 'Acknowledgment of Operational Terms — Filed in Triplicate'."""
    cert_uuid = str(uuid_lib.uuid4())
    registry_id = generate_compliance_id()

    name = (request.name or '').strip() or 'Anonymous Acknowledger'

    receipt = {
        'uuid': cert_uuid,
        'registry_id': registry_id,
        'name': name,
        'confession': None,
        'severity_class': 'Compliance',
        'stability': 'Procedurally Compliant',
        'risk_score': 0,
        'protocol': 'Acknowledgment of Operational Terms — Filed in Triplicate',
        'status': 'Acknowledged',
        'tier': 'compliance',
        'receipt_type': 'tc_acknowledgment',
        'jurisdiction': request.jurisdiction or 'Unspecified',
        'acknowledgments': request.acknowledgments or [
            'Operational Terms',
            'Jurisdictional Disclaimer',
            'Privacy Policy',
            'Contribution Policy',
        ],
        'payment_amount': 0.0,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }

    await db.certificates.insert_one(receipt)

    logger.info(f"Compliance receipt {registry_id} for {name}")

    return {
        'uuid': cert_uuid,
        'registry_id': registry_id,
        'name': name,
        'status': 'Acknowledged',
        'tier': 'compliance',
        'protocol': receipt['protocol'],
        'jurisdiction': receipt['jurisdiction'],
        'acknowledgments': receipt['acknowledgments'],
        'created_at': receipt['created_at'],
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
    cert = await db.certificates.find_one({'registry_id': registry_id}, {'_id': 0})
    
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



@api_router.post("/plisio/invoice")
async def plisio_invoice_endpoint(request: CheckoutRequest):
    """Create Plisio crypto invoice (BTC, LTC, USDT TRC/BEP, TRX, TON, DOGE etc.)"""
    if request.tier not in PLISIO_PRICING:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    cert = await db.certificates.find_one({'uuid': request.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    try:
        result = await plisio_create_invoice(
            tier=request.tier,
            certificate_uuid=request.certificate_uuid,
            origin_url=request.origin_url,
            backend_url=BASE_URL,
        )
        
        transaction = {
            'session_id': result['txn_id'],
            'plisio_txn_id': result['txn_id'],
            'order_id': result['order_id'],
            'certificate_uuid': request.certificate_uuid,
            'amount': result['amount_usd'],
            'currency': 'usd',
            'tier': request.tier,
            'payment_method': 'plisio',
            'status': 'pending',
            'payment_status': 'unpaid',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(transaction)
        
        logger.info(f"Plisio invoice {result['txn_id']} for cert {request.certificate_uuid}")
        return {'url': result['url'], 'txn_id': result['txn_id']}
        
    except Exception as e:
        logger.error(f"Plisio invoice error: {e}")
        raise HTTPException(status_code=500, detail=f"Invoice creation failed: {str(e)}")


@api_router.get("/plisio/status/{certificate_uuid}")
async def plisio_status(certificate_uuid: str):
    """Check Plisio payment status by certificate uuid"""
    cert = await db.certificates.find_one({'uuid': certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return {
        'tier': cert.get('tier', 'free'),
        'status': cert.get('status', 'temporary'),
        'is_paid': cert.get('tier') == 'paid',
    }


@api_router.api_route("/webhooks/plisio", methods=["GET", "POST"])
async def plisio_webhook(request: Request):
    """
    Handle Plisio webhook.
    Plisio sends POST as application/x-www-form-urlencoded (not JSON).
    Signature: HMAC-SHA1 of PHP serialize(ksort(payload_without_verify_hash))
    """
    content_type = request.headers.get('content-type', '')
    try:
        if request.method == 'GET':
            payload = dict(request.query_params)
        elif 'application/json' in content_type:
            payload = await request.json()
        else:
            # Default: form-urlencoded (Plisio default)
            form = await request.form()
            payload = {k: str(v) for k, v in form.items()}
    except Exception as e:
        logger.error(f"Plisio webhook payload parse error: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    received_hash = payload.get('verify_hash')
    if not received_hash:
        logger.warning(f"Plisio webhook missing verify_hash. Content-Type={content_type} keys={list(payload.keys())}")
        raise HTTPException(status_code=400, detail="Missing verify_hash")
    
    if not plisio_verify_signature(payload, received_hash):
        logger.error(f"Plisio webhook invalid signature: txn={payload.get('txn_id')}")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    status = payload.get('status', '')
    order_id = payload.get('order_number', '')
    amount = payload.get('source_amount') or payload.get('amount') or '0'
    paid_currency = payload.get('currency', 'crypto')
    txn_id = payload.get('txn_id', '')
    
    logger.info(f"Plisio webhook: status={status}, order={order_id}, txn={txn_id}")
    
    cert_uuid = order_id.split('_')[0] if order_id else None
    if not cert_uuid:
        raise HTTPException(status_code=400, detail="Invalid order_number")
    
    normalized = plisio_normalize_status(status)
    
    await db.payment_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'payment_status': normalized,
            'plisio_status': status,
            'paid_amount': amount,
            'paid_currency': paid_currency,
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
                    'payment_amount': float(amount) if amount else 0.0,
                    'payment_method': f'plisio_{paid_currency}',
                }}
            )
            logger.info(f"Certificate {cert_uuid} upgraded via Plisio ({paid_currency})")
    
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


def _build_certificate_email_html(cert: dict, message: str = None) -> str:
    """Build branded HTML email with cert details + AI sketch watermark."""
    verification_url = f"{BASE_URL}/verify/{cert['registry_id']}"
    severity_color = {
        'Critical': '#D92D20',
        'High': '#B45309',
        'Moderate': '#525252',
    }.get(cert.get('severity_class', 'Low'), '#15803D')
    
    sketch_block = ''
    if cert.get('sketch_url'):
        sketch_block = f'''
        <tr><td align="center" style="padding:20px 0;">
            <img src="{cert['sketch_url']}" alt="" width="240"
                 style="display:block;opacity:0.85;filter:grayscale(100%);max-width:240px;height:auto;"/>
            <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;margin-top:8px;">
                Personalized Imprint
            </div>
        </td></tr>'''
    
    confession_block = ''
    if cert.get('confession'):
        confession_block = f'''
        <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
            <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">
                Incident Report
            </div>
            <blockquote style="margin:0;padding:10px 14px;border-left:3px solid #0A0A0A;background:#F4F4F0;font-family:monospace;font-size:13px;color:#0A0A0A;white-space:pre-wrap;">
                {cert['confession']}
            </blockquote>
        </td></tr>'''
    
    message_block = ''
    if message:
        message_block = f'''
        <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
            <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">
                Accompanying Notice
            </div>
            <div style="font-size:14px;color:#0A0A0A;line-height:1.5;">{message}</div>
        </td></tr>'''
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:24px;background:#F4F4F0;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px;margin:0 auto;">
    <tr><td style="background:#FFFFFF;border:2px solid #0A0A0A;padding:28px;">
        <table cellpadding="0" cellspacing="0" border="0" width="100%">
            <tr><td>
                <div style="font-size:24px;font-weight:900;text-transform:uppercase;letter-spacing:-1px;color:#0A0A0A;">Karma Cleanse</div>
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Official Certificate v2.1</div>
            </td></tr>
            <tr><td style="padding-top:20px;border-top:1px solid #E5E5DF;margin-top:20px;">&nbsp;</td></tr>
            <tr><td>
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Registry ID</div>
                <div style="font-size:22px;font-weight:900;color:#0A0A0A;margin-top:4px;">{cert['registry_id']}</div>
            </td></tr>
            <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Subject</div>
                <div style="font-family:monospace;font-size:14px;color:#0A0A0A;margin-top:4px;">{cert.get('name') or 'Anonymous Entity'}</div>
            </td></tr>
            {confession_block}
            <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">Classification</div>
                <span style="display:inline-block;padding:6px 14px;border:2px solid {severity_color};color:{severity_color};font-size:16px;font-weight:900;text-transform:uppercase;letter-spacing:2px;">CLASS {cert['severity_class'].upper()}</span>
            </td></tr>
            <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                    <tr>
                        <td width="50%">
                            <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Stability</div>
                            <div style="font-family:monospace;font-size:13px;color:#0A0A0A;margin-top:4px;">{cert['stability']}</div>
                        </td>
                        <td width="50%">
                            <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Risk Score</div>
                            <div style="font-family:monospace;font-size:13px;color:#0A0A0A;margin-top:4px;">{cert['risk_score']}/100</div>
                        </td>
                    </tr>
                </table>
            </td></tr>
            <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Protocol Applied</div>
                <div style="font-family:monospace;font-size:13px;color:#0A0A0A;margin-top:4px;">{cert['protocol']}</div>
            </td></tr>
            <tr><td style="padding-top:16px;border-top:1px solid #E5E5DF;">
                <div style="font-family:monospace;font-size:10px;color:#737373;letter-spacing:2px;text-transform:uppercase;">Status</div>
                <div style="font-family:monospace;font-size:13px;font-weight:bold;color:{'#15803D' if cert.get('tier')=='paid' else '#B45309'};margin-top:4px;text-transform:uppercase;">
                    {cert.get('status','Issued').upper()} — {cert.get('tier','free').upper()} TIER
                </div>
            </td></tr>
            {sketch_block}
            {message_block}
            <tr><td style="padding-top:20px;border-top:2px solid #0A0A0A;margin-top:20px;text-align:center;">
                <a href="{verification_url}" style="display:inline-block;padding:12px 24px;background:#0A0A0A;color:#FFFFFF;text-decoration:none;font-weight:900;text-transform:uppercase;letter-spacing:2px;font-size:12px;">Verify Certificate</a>
                <div style="font-family:monospace;font-size:10px;color:#737373;margin-top:12px;word-break:break-all;">{verification_url}</div>
            </td></tr>
            <tr><td style="padding-top:20px;text-align:center;">
                <div style="font-family:monospace;font-size:10px;color:#737373;line-height:1.6;">
                    This certificate represents administrative absolution only.<br/>
                    Not legally binding. Emotional bureaucracy since 2026.
                </div>
            </td></tr>
        </table>
    </td></tr>
</table>
</body></html>"""


async def _send_certificate_email_via_resend(cert: dict, recipient_email: str, message: str = None) -> dict:
    """Internal helper: actually sends the email via Resend API."""
    html_content = _build_certificate_email_html(cert, message)
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": f"Karma Cleanse Certificate \u2014 {cert['registry_id']}",
        "html": html_content,
    }
    email_result = await asyncio.to_thread(resend.Emails.send, params)
    return email_result


class SendNowRequest(BaseModel):
    certificate_uuid: str
    recipient_email: EmailStr
    message: Optional[str] = None


@api_router.post("/delivery/send-now")
async def send_certificate_email_now(req: SendNowRequest):
    """Send certificate email immediately."""
    cert = await db.certificates.find_one({'uuid': req.certificate_uuid}, {'_id': 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    try:
        result = await _send_certificate_email_via_resend(cert, req.recipient_email, req.message)
        logger.info(f"Email sent to {req.recipient_email}, id={result.get('id')}")
        return {'sent': True, 'recipient': req.recipient_email, 'email_id': result.get('id')}
    except Exception as e:
        logger.error(f"Send-now failed: {e}")
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")


# --- Background scheduler -------------------------------------------------
async def _scheduled_delivery_worker():
    """Polls scheduled_deliveries every 30s, sends due ones via Resend."""
    while True:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor = db.scheduled_deliveries.find(
                {'sent': False, 'send_at': {'$lte': now_iso}},
                {'_id': 0},
            )
            due = await cursor.to_list(length=50)
            for d in due:
                cert = await db.certificates.find_one(
                    {'uuid': d['certificate_uuid']}, {'_id': 0}
                )
                if not cert:
                    await db.scheduled_deliveries.update_one(
                        {'certificate_uuid': d['certificate_uuid'],
                         'recipient_email': d['recipient_email'],
                         'send_at': d['send_at']},
                        {'$set': {'sent': True, 'failed': True, 'error': 'cert_not_found',
                                  'sent_at': datetime.now(timezone.utc).isoformat()}}
                    )
                    continue
                try:
                    result = await _send_certificate_email_via_resend(
                        cert, d['recipient_email'], d.get('message')
                    )
                    await db.scheduled_deliveries.update_one(
                        {'certificate_uuid': d['certificate_uuid'],
                         'recipient_email': d['recipient_email'],
                         'send_at': d['send_at']},
                        {'$set': {
                            'sent': True,
                            'sent_at': datetime.now(timezone.utc).isoformat(),
                            'email_id': result.get('id'),
                        }}
                    )
                    logger.info(f"[worker] sent scheduled delivery to {d['recipient_email']} id={result.get('id')}")
                except Exception as send_err:
                    logger.error(f"[worker] failed delivery to {d['recipient_email']}: {send_err}")
                    await db.scheduled_deliveries.update_one(
                        {'certificate_uuid': d['certificate_uuid'],
                         'recipient_email': d['recipient_email'],
                         'send_at': d['send_at']},
                        {'$set': {
                            'last_error': str(send_err),
                            'last_attempt_at': datetime.now(timezone.utc).isoformat(),
                            'attempts': d.get('attempts', 0) + 1,
                        }}
                    )
                    # Mark as failed after 5 attempts
                    if d.get('attempts', 0) + 1 >= 5:
                        await db.scheduled_deliveries.update_one(
                            {'certificate_uuid': d['certificate_uuid'],
                             'recipient_email': d['recipient_email'],
                             'send_at': d['send_at']},
                            {'$set': {'sent': True, 'failed': True}}
                        )
        except Exception as e:
            logger.error(f"[worker] loop error: {e}")
        await asyncio.sleep(30)


# --- Resend webhook (delivery/open/click tracking) -----------------------
RESEND_WEBHOOK_SECRET = os.environ.get('RESEND_WEBHOOK_SECRET', '')


@api_router.post("/webhooks/resend")
async def resend_webhook(request: Request):
    """Receive Resend (Svix) webhooks: email.sent / .delivered / .opened / .clicked / .bounced / .complained."""
    raw_body = await request.body()
    headers = dict(request.headers)

    # Verify signature if secret configured
    if RESEND_WEBHOOK_SECRET:
        try:
            from svix.webhooks import Webhook, WebhookVerificationError
            wh = Webhook(RESEND_WEBHOOK_SECRET)
            wh.verify(raw_body, headers)
        except WebhookVerificationError as e:
            logger.error(f"Resend webhook invalid signature: {e}")
            raise HTTPException(status_code=403, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Resend webhook verification error: {e}")
            raise HTTPException(status_code=400, detail="Verification error")
    else:
        logger.warning("RESEND_WEBHOOK_SECRET not configured — skipping signature verification")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get('type', '')
    event_data = payload.get('data', {})
    email_id = event_data.get('email_id') or event_data.get('id')
    created_at = payload.get('created_at') or datetime.now(timezone.utc).isoformat()

    # Persist event
    await db.email_events.insert_one({
        'event_type': event_type,
        'email_id': email_id,
        'to': event_data.get('to'),
        'subject': event_data.get('subject'),
        'click_url': event_data.get('click', {}).get('link') if isinstance(event_data.get('click'), dict) else None,
        'bounce_type': event_data.get('bounce', {}).get('type') if isinstance(event_data.get('bounce'), dict) else None,
        'raw': event_data,
        'received_at': datetime.now(timezone.utc).isoformat(),
        'event_at': created_at,
    })

    # Update scheduled_deliveries metrics
    update = {}
    if event_type == 'email.delivered':
        update['delivered_at'] = created_at
    elif event_type == 'email.opened':
        update['opened_at'] = created_at
    elif event_type == 'email.clicked':
        update['clicked_at'] = created_at
    elif event_type == 'email.bounced':
        update['bounced_at'] = created_at
    elif event_type == 'email.complained':
        update['complained_at'] = created_at

    if update and email_id:
        await db.scheduled_deliveries.update_one(
            {'email_id': email_id},
            {'$set': update}
        )

    logger.info(f"Resend event: {event_type} email={email_id}")
    return {'received': True}


@api_router.get("/email-events/{email_id}")
async def get_email_events(email_id: str):
    """Get the timeline of events for a specific email."""
    events = await db.email_events.find(
        {'email_id': email_id},
        {'_id': 0, 'raw': 0},
    ).sort('event_at', 1).to_list(length=50)
    return {'email_id': email_id, 'events': events}


@app.on_event("startup")
async def _start_delivery_worker():
    asyncio.create_task(_scheduled_delivery_worker())
    logger.info("Scheduled delivery worker started (interval=30s)")


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
