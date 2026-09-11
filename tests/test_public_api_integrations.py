"""
Unit and integration tests for the 6 Public API Integrations:
1. Search & Discovery (GitHub / Developer repo discovery)
2. Weather & Environmental Forecast
3. Maps & Geolocation (Commute calculation via Haversine)
4. Payments & eCommerce (Stripe checkout & HMAC signature verification)
5. Social & Messaging (Slack/Teams notification dispatching)
6. Service Management & Cloud DNS
"""

import time
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport

from src.api import app
from src.services.public_api_service import PublicApiService


@pytest.mark.asyncio
async def test_search_and_discovery_service():
    """Verify search & discovery connector returns formatted search items."""
    res = await PublicApiService.search_discovery(query="fastapi", platform="github", limit=3)
    assert res["query"] == "fastapi"
    assert len(res["results"]) >= 1
    item = res["results"][0]
    assert "name" in item
    assert "url" in item
    assert "stars" in item


@pytest.mark.asyncio
async def test_weather_and_environmental_forecast():
    """Verify weather connector returns temperatures and interview advisories."""
    res = await PublicApiService.get_weather_forecast(city="Seattle")
    assert res["city"] == "Seattle"
    assert "temperature_c" in res
    assert "temperature_f" in res
    assert "condition" in res
    assert "interview_advisory" in res


def test_maps_and_commute_calculation():
    """Verify Haversine formula calculation and commute eligibility."""
    # San Francisco (37.7749, -122.4194) to Mountain View (37.3861, -122.0839) ~ 50 km
    res = PublicApiService.calculate_commute_distance(
        origin_lat=37.7749, origin_lng=-122.4194,
        dest_lat=37.3861, dest_lng=-122.0839
    )
    assert 40.0 < res["distance_km"] < 65.0
    assert res["distance_miles"] > 25.0
    assert res["estimated_drive_minutes"] > 30
    assert "hybrid_commute_eligible" in res


def test_payments_checkout_and_webhook_hmac():
    """Verify Stripe-style checkout session generation and HMAC-SHA256 signature verification."""
    # 1. Checkout session
    checkout = PublicApiService.create_checkout_session(
        org_id="org_test_123",
        plan_tier="growth",
        candidate_credits=20
    )
    assert checkout["session_id"].startswith("cs_test_")
    assert checkout["total_usd"] == 20 * 12
    assert "checkout.stripe.com" in checkout["payment_url"]

    # 2. Webhook verification
    secret = "whsec_test_secret_abc123"
    payload = '{"type": "payment_intent.succeeded", "amount": 24000}'
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={sig}"

    # Valid signature
    verify_res = PublicApiService.verify_payment_webhook(
        payload=payload,
        signature_header=sig_header,
        secret=secret
    )
    assert verify_res["valid"] is True

    # Invalid signature tampering
    tampered_sig_header = f"t={timestamp},v1=deadbeef00000000000000000000000000000000000000000000000000000000"
    tampered_res = PublicApiService.verify_payment_webhook(
        payload=payload,
        signature_header=tampered_sig_header,
        secret=secret
    )
    assert tampered_res["valid"] is False


@pytest.mark.asyncio
async def test_social_and_messaging_dispatch():
    """Verify recruiter alert notification formatting and dispatch."""
    res = await PublicApiService.dispatch_recruiter_alert(
        channel_type="slack",
        webhook_url=None,  # simulated delivery
        event_title="Assessment Submission",
        message="Candidate completed test with 95%",
        candidate_name="Alice Candidate",
        score=95
    )
    assert res["delivered"] is True
    assert res["payload"]["score"] == 95
    assert res["channel_type"] == "slack"


@pytest.mark.asyncio
async def test_service_management_dns_check():
    """Verify custom domain DNS and CNAME resolution."""
    res = await PublicApiService.check_custom_domain_dns(domain="careers.mycompany.com")
    assert res["domain"] == "careers.mycompany.com"
    assert res["cname_target"] == "cname.auditagent.ai"
    assert "is_reachable" in res


@pytest.mark.asyncio
async def test_integrations_rest_api_endpoints():
    """Verify HTTP API endpoints in /api/v1/integrations/*."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Catalog
        cat_res = await ac.get("/api/v1/integrations/catalog")
        assert cat_res.status_code == 200
        cat_data = cat_res.json()
        assert cat_data["total_integrations"] == 6

        # 2. Search
        s_res = await ac.post("/api/v1/integrations/search", json={"query": "react", "limit": 3})
        assert s_res.status_code == 200
        assert s_res.json()["query"] == "react"

        # 3. Weather
        w_res = await ac.get("/api/v1/integrations/weather?city=Austin")
        assert w_res.status_code == 200
        assert w_res.json()["city"] == "Austin"

        # 4. Maps Commute
        m_res = await ac.post("/api/v1/integrations/maps/commute", json={
            "origin_lat": 37.7749, "origin_lng": -122.4194,
            "dest_lat": 37.3861, "dest_lng": -122.0839
        })
        assert m_res.status_code == 200
        assert "distance_km" in m_res.json()

        # 5. Payments Checkout
        p_res = await ac.post("/api/v1/integrations/payments/checkout", json={
            "org_id": "org_999",
            "plan_tier": "enterprise",
            "candidate_credits": 50
        })
        assert p_res.status_code == 200
        assert p_res.json()["total_usd"] == 50 * 8

        # 6. Messaging Notify
        n_res = await ac.post("/api/v1/integrations/notify", json={
            "channel_type": "teams",
            "event_title": "Proctoring Alert",
            "message": "Candidate tab switch detected.",
            "candidate_name": "Bob Tester",
            "score": 50
        })
        assert n_res.status_code == 200
        assert n_res.json()["delivered"] is True

        # 7. DNS Check
        d_res = await ac.post("/api/v1/integrations/dns/check", json={"domain": "jobs.techcorp.io"})
        assert d_res.status_code == 200
        assert "cname_target" in d_res.json()
