"""Karma Cleanse v2.1 backend API tests"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cleansing-ritual.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# Health check
def test_root(session):
    r = session.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    assert "Karma" in r.json().get("message", "")


# Severity analysis
def test_analyze_too_short(session):
    r = session.post(f"{BASE_URL}/api/analyze", json={"confession": "hi"})
    assert r.status_code == 400


def test_analyze_valid(session):
    r = session.post(f"{BASE_URL}/api/analyze", json={"confession": "I ghosted my friend after she lied to me about a betrayed promise."})
    assert r.status_code == 200
    data = r.json()
    for k in ("severity_class", "stability", "risk_score", "protocol", "diagnostics"):
        assert k in data
    assert data["severity_class"] in ("Low", "Moderate", "High", "Critical")
    assert isinstance(data["risk_score"], int)
    assert isinstance(data["diagnostics"], list)


# Certificate creation + retrieval
@pytest.fixture(scope="module")
def created_cert(session):
    analyze = session.post(f"{BASE_URL}/api/analyze", json={"confession": "I forgot a friend's birthday and made an awkward excuse."}).json()
    payload = {
        "name": "TEST_User",
        "confession": "I forgot a friend's birthday and made an awkward excuse.",
        **{k: analyze[k] for k in ("severity_class", "stability", "risk_score", "protocol", "diagnostics")}
    }
    r = session.post(f"{BASE_URL}/api/certificate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "uuid" in data and "registry_id" in data
    assert data["tier"] == "free"
    assert data["status"] == "temporary"
    # Registry format KR-YYYY-XX#### per problem statement
    assert data["registry_id"].startswith("KR-")
    return data


def test_get_certificate(session, created_cert):
    r = session.get(f"{BASE_URL}/api/certificate/{created_cert['uuid']}")
    assert r.status_code == 200
    cert = r.json()
    assert cert["uuid"] == created_cert["uuid"]
    assert cert["name"] == "TEST_User"
    assert cert["tier"] == "free"
    assert "_id" not in cert


def test_get_certificate_404(session):
    r = session.get(f"{BASE_URL}/api/certificate/nonexistent-uuid")
    assert r.status_code == 404


# Checkout
def test_checkout_invalid_tier(session, created_cert):
    r = session.post(f"{BASE_URL}/api/checkout/session", json={
        "tier": "bogus", "certificate_uuid": created_cert["uuid"], "origin_url": BASE_URL
    })
    assert r.status_code == 400


def test_checkout_cert_not_found(session):
    r = session.post(f"{BASE_URL}/api/checkout/session", json={
        "tier": "standard", "certificate_uuid": "missing", "origin_url": BASE_URL
    })
    assert r.status_code == 404


def test_checkout_standard(session, created_cert):
    r = session.post(f"{BASE_URL}/api/checkout/session", json={
        "tier": "standard", "certificate_uuid": created_cert["uuid"], "origin_url": BASE_URL
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "url" in data and "session_id" in data
    assert "stripe" in data["url"].lower() or "checkout" in data["url"].lower()


# Delivery
def test_delivery_schedule(session, created_cert):
    r = session.post(f"{BASE_URL}/api/delivery/schedule", json={
        "certificate_uuid": created_cert["uuid"],
        "recipient_email": "test@example.com",
        "message": "TEST",
        "delay_hours": 24,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["scheduled"] is True
    assert data["recipient"] == "test@example.com"


def test_delivery_invalid_email(session, created_cert):
    r = session.post(f"{BASE_URL}/api/delivery/schedule", json={
        "certificate_uuid": created_cert["uuid"],
        "recipient_email": "not-an-email",
        "delay_hours": 24,
    })
    assert r.status_code == 422


def test_delivery_invalid_hours(session, created_cert):
    r = session.post(f"{BASE_URL}/api/delivery/schedule", json={
        "certificate_uuid": created_cert["uuid"],
        "recipient_email": "test@example.com",
        "delay_hours": 999,
    })
    assert r.status_code == 422


def test_delivery_cert_not_found(session):
    r = session.post(f"{BASE_URL}/api/delivery/schedule", json={
        "certificate_uuid": "missing",
        "recipient_email": "test@example.com",
        "delay_hours": 24,
    })
    assert r.status_code == 404
