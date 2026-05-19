from fastapi import FastAPI, APIRouter, HTTPException, Request, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
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
