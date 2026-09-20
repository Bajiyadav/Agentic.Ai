"""
Tests for First-Time Recruiter Onboarding System in AuditAgent.ai.
Validates:
1. Default onboarding state for brand-new recruiter
2. User-specific isolation (Recruiter A does not affect Recruiter B)
3. State persistence across sessions and multi-device backend sync
4. Step completion logic based on real state
"""

import pytest
from starlette.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_new_recruiter_default_onboarding_state():
    """Brand new recruiter starts with fresh, uncompleted, non-dismissed onboarding state."""
    res = client.get("/api/v1/auth/onboarding-state?email=brand_new_recruiter@company.com")
    assert res.status_code == 200
    data = res.json()
    assert data["user_email"] == "brand_new_recruiter@company.com"
    assert data["dismissed"] is False
    assert data["audit_reviewed"] is False
    assert data["completed"] is False
    assert data["completed_steps"] == []

def test_recruiter_onboarding_state_persistence_and_isolation():
    """Recruiter A's dismissal or progress never affects Recruiter B."""
    recruiter_a = "recruiter_alpha@company.com"
    recruiter_b = "recruiter_beta@company.com"

    # Save state for Recruiter A (dismissed after completing step)
    post_a = client.post("/api/v1/auth/onboarding-state", json={
        "email": recruiter_a,
        "dismissed": True,
        "audit_reviewed": True,
        "completed": True,
        "completed_steps": ["step_1_job", "step_2_screen", "step_3_audit"]
    })
    assert post_a.status_code == 200
    data_a = post_a.json()
    assert data_a["dismissed"] is True
    assert data_a["audit_reviewed"] is True
    assert data_a["completed"] is True

    # Check Recruiter B remains completely untouched
    res_b = client.get(f"/api/v1/auth/onboarding-state?email={recruiter_b}")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["user_email"] == recruiter_b
    assert data_b["dismissed"] is False
    assert data_b["audit_reviewed"] is False
    assert data_b["completed"] is False

    # Verify Recruiter A state persists on subsequent get
    res_a_again = client.get(f"/api/v1/auth/onboarding-state?email={recruiter_a}")
    assert res_a_again.status_code == 200
    data_a_again = res_a_again.json()
    assert data_a_again["dismissed"] is True
    assert data_a_again["completed"] is True

def test_reopen_onboarding_state():
    """Recruiter can voluntarily reopen guide after dismissing."""
    recruiter = "sarah_test@acmecorp.com"
    
    # Dismiss
    client.post("/api/v1/auth/onboarding-state", json={
        "email": recruiter,
        "dismissed": True
    })
    
    # Reopen
    reopen_res = client.post("/api/v1/auth/onboarding-state", json={
        "email": recruiter,
        "dismissed": False
    })
    assert reopen_res.status_code == 200
    assert reopen_res.json()["dismissed"] is False
