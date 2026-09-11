"""
Public API Integrations Router:
Exposes REST endpoints for the 6 major public API categories:
1. Search & Discovery
2. Weather & Forecast
3. Maps & Geolocation
4. Payments & eCommerce
5. Social & Messaging
6. Service Management & DNS
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.public_api_service import PublicApiService

router = APIRouter(prefix="/api/v1/integrations", tags=["Public API Integrations"])


# -------------------------------------------------------------
# Request & Response Models
# -------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., examples=["FastAPI"])
    platform: str = Field(default="github", examples=["github"])
    limit: Optional[int] = Field(default=5, ge=1, le=20)

class CommuteRequest(BaseModel):
    origin_lat: float = Field(..., examples=[37.7749])
    origin_lng: float = Field(..., examples=[-122.4194])
    dest_lat: float = Field(..., examples=[37.3861])
    dest_lng: float = Field(..., examples=[-122.0839])

class CheckoutRequest(BaseModel):
    org_id: str = Field(..., examples=["org_123"])
    plan_tier: str = Field(default="growth", examples=["growth"])
    candidate_credits: int = Field(default=25, ge=1, le=500)

class WebhookVerifyRequest(BaseModel):
    payload: str = Field(..., examples=['{"type": "payment_intent.succeeded", "amount": 2500}'])
    signature_header: str = Field(..., examples=["t=1700000000,v1=abc123..."])
    secret: str = Field(..., examples=["whsec_test_secret_key"])

class NotifyRequest(BaseModel):
    channel_type: str = Field(default="slack", examples=["slack"])
    webhook_url: Optional[str] = Field(default=None, examples=["https://hooks.slack.com/services/..."])
    event_title: str = Field(..., examples=["Candidate Assessment Completed"])
    message: str = Field(..., examples=["Candidate John Doe scored 88/100 in Software Engineer track."])
    candidate_name: str = Field(..., examples=["John Doe"])
    score: Optional[int] = Field(default=88)

class DnsCheckRequest(BaseModel):
    domain: str = Field(..., examples=["careers.mycompany.com"])


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.get("/catalog")
def get_integrations_catalog():
    """Returns the catalog of the 6 core public API integrations available in AuditAgent."""
    return {
        "total_integrations": 6,
        "integrations": [
            {
                "id": "search_discovery",
                "name": "Search & Discovery API",
                "icon": "🔍",
                "category": "Content & Code Aggregation",
                "description": "Discover open-source repositories, developer portfolios, and technical video content.",
                "example_provider": "GitHub API / YouTube Data API",
                "endpoint": "POST /api/v1/integrations/search"
            },
            {
                "id": "weather_forecast",
                "name": "Weather & Environmental API",
                "icon": "☀️",
                "category": "Location Context",
                "description": "Real-time atmospheric conditions and interview connectivity forecasting by candidate city.",
                "example_provider": "OpenWeatherMap API",
                "endpoint": "GET /api/v1/integrations/weather"
            },
            {
                "id": "maps_geolocation",
                "name": "Maps & Commute Geolocation API",
                "icon": "🗺️",
                "category": "Spatial Computing",
                "description": "Great-circle distance, commute duration calculation, and hybrid office eligibility checking.",
                "example_provider": "Google Maps Platform",
                "endpoint": "POST /api/v1/integrations/maps/commute"
            },
            {
                "id": "payments_ecommerce",
                "name": "Payments & Subscription Billing API",
                "icon": "💳",
                "category": "Fintech & eCommerce",
                "description": "Checkout session creation, plan tier upgrade billing, and HMAC-SHA256 webhook verification.",
                "example_provider": "Stripe API",
                "endpoint": "POST /api/v1/integrations/payments/checkout"
            },
            {
                "id": "social_messaging",
                "name": "Social & Recruiter Messaging Webhooks",
                "icon": "💬",
                "category": "Communication & Alerts",
                "description": "Dispatch automated assessment completion and proctoring alert notifications to Slack or Teams.",
                "example_provider": "Slack Webhooks / X API",
                "endpoint": "POST /api/v1/integrations/notify"
            },
            {
                "id": "service_management",
                "name": "Service Management & Cloud DNS API",
                "icon": "⚙️",
                "category": "Infrastructure & Hosting",
                "description": "Automated DNS record validation, SSL certificate checks, and CNAME propagation status.",
                "example_provider": "Hostinger / Cloudflare API",
                "endpoint": "POST /api/v1/integrations/dns/check"
            }
        ]
    }


@router.post("/search")
async def execute_search(req: SearchRequest):
    """Search developer and repository assets across external platforms."""
    return await PublicApiService.search_discovery(
        query=req.query,
        platform=req.platform,
        limit=req.limit or 5
    )


@router.get("/weather")
async def get_weather(city: str = Query(default="San Francisco", description="City name to fetch forecast for")):
    """Get atmospheric conditions and video-interview advisory for a candidate's location."""
    return await PublicApiService.get_weather_forecast(city=city)


@router.post("/maps/commute")
def calculate_commute(req: CommuteRequest):
    """Calculate Haversine distance, estimated drive/transit durations, and commute eligibility."""
    return PublicApiService.calculate_commute_distance(
        origin_lat=req.origin_lat,
        origin_lng=req.origin_lng,
        dest_lat=req.dest_lat,
        dest_lng=req.dest_lng
    )


@router.post("/payments/checkout")
def create_checkout(req: CheckoutRequest):
    """Create an idempotent checkout session for candidate assessment credits or plan upgrades."""
    return PublicApiService.create_checkout_session(
        org_id=req.org_id,
        plan_tier=req.plan_tier,
        candidate_credits=req.candidate_credits
    )


@router.post("/payments/verify-webhook")
def verify_webhook(req: WebhookVerifyRequest):
    """Verify an HMAC-SHA256 signature for incoming payment webhook payloads."""
    return PublicApiService.verify_payment_webhook(
        payload=req.payload,
        signature_header=req.signature_header,
        secret=req.secret
    )


@router.post("/notify")
async def dispatch_notification(req: NotifyRequest):
    """Dispatch real-time recruiter alert notifications to external Slack, Discord, or generic Webhook endpoints."""
    return await PublicApiService.dispatch_recruiter_alert(
        channel_type=req.channel_type,
        webhook_url=req.webhook_url,
        event_title=req.event_title,
        message=req.message,
        candidate_name=req.candidate_name,
        score=req.score
    )


@router.post("/dns/check")
async def check_custom_domain(req: DnsCheckRequest):
    """Verify DNS routing, CNAME configuration, and SSL reachability for custom domains."""
    return await PublicApiService.check_custom_domain_dns(domain=req.domain)
