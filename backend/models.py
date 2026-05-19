from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class CertificateCreate(BaseModel):
    name: Optional[str] = None
    confession: str
    severity_class: str
    stability: str
    risk_score: int
    protocol: str
    diagnostics: List[str]

class Certificate(BaseModel):
    uuid: str
    registry_id: str
    name: Optional[str] = None
    confession: str
    severity_class: str
    stability: str
    risk_score: int
    protocol: str
    diagnostics: List[str]
    status: str  # temporary or certified
    tier: str  # free or paid
    payment_amount: float = 0.0
    created_at: str

class SeverityAnalysis(BaseModel):
    severity_class: str
    stability: str
    risk_score: int
    protocol: str
    diagnostics: List[str]

class AnalyzeRequest(BaseModel):
    confession: str

class CheckoutRequest(BaseModel):
    tier: str  # standard, premium, enterprise
    certificate_uuid: str
    origin_url: str

class CryptoPaymentRequest(BaseModel):
    tier: str  # standard, premium, enterprise
    certificate_uuid: str
    tx_hash: str
    sender_address: Optional[str] = None

class DeliveryRequest(BaseModel):
    certificate_uuid: str
    recipient_email: EmailStr
    message: Optional[str] = None
    delay_hours: int = Field(ge=1, le=168)  # 1-168 hours (1 week max)

class PaymentTransaction(BaseModel):
    session_id: str
    certificate_uuid: str
    amount: float
    currency: str = "usd"
    status: str = "pending"
    payment_status: str = "unpaid"
    created_at: str