import os
from unittest.mock import AsyncMock, patch

import pytest

@pytest.mark.skipif(
    os.getenv("APP_ENV") == "test",
    reason="Requires Redis/Celery broker"
)
def test_report_issue_and_suggest_classification(client, db_session):
    # Setup users
    client.post("/api/auth/signup", json={"name": "Alice Admin", "email": "alice@example.com", "password": "password123", "role": "Admin"})
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    csrf_token = login_res.json()["csrf_token"]
    cookies = login_res.cookies

    # Test categorization Suggestion (MOCK External Failure -> Fallback to keyword)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Connection Refused")

        suggest_res = client.post(
            "/api/issues/suggest-classification",
            data={"title": "Severe water leakage in main street", "description": "There is water bursting from the pipes and flooding the road."},
            cookies=cookies
        )
        assert suggest_res.status_code == 200
        suggest_data = suggest_res.json()
        assert suggest_data["category"] == "Water Leakage"
        assert suggest_data["priority"] == "Medium"
        assert "Local keyword match" in suggest_data["reasoning"]

    # Test reporting issue
    report_res = client.post(
        "/api/issues",
        data={
            "title": "Severe pothole near street corner",
            "description": "Deep pothole causing road bumps and hazard to vehicles.",
            "category": "Potholes",
            "priority": "Medium",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        headers={"X-CSRF-Token": csrf_token},
        cookies=cookies
    )
    assert report_res.status_code == 200
    report_data = report_res.json()
    assert report_data["title"] == "Severe pothole near street corner"
    assert report_data["status"] == "Open"

@pytest.mark.skipif(
    os.getenv("APP_ENV") == "test",
    reason="Requires Redis/Celery broker"
)
def test_verification_escalation_flow(client, db_session):
    # Setup Reporter and Verifiers
    client.post("/api/auth/signup", json={"name": "Reporter", "email": "reporter@example.com", "password": "password123", "role": "Citizen"})
    client.post("/api/auth/signup", json={"name": "Verifier 1", "email": "v1@example.com", "password": "password123", "role": "Citizen"})
    client.post("/api/auth/signup", json={"name": "Verifier 2", "email": "v2@example.com", "password": "password123", "role": "Citizen"})

    # Login Reporter
    rep_login = client.post("/api/auth/login", json={"email": "reporter@example.com", "password": "password123"})
    rep_csrf = rep_login.json()["csrf_token"]
    rep_cookies = rep_login.cookies

    # Submit Issue
    issue_res = client.post(
        "/api/issues",
        data={
            "title": "Broken streetlamp in dark lane",
            "description": "The lamp is completely broken causing dark unsafe pathway.",
            "category": "Damaged Streetlights",
            "priority": "Low",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        headers={"X-CSRF-Token": rep_csrf},
        cookies=rep_cookies
    )
    issue_id = issue_res.json()["id"]

    # Try self-verification (should fail)
    self_verify = client.post(
        "/api/verifications",
        json={"issue_id": issue_id},
        headers={"X-CSRF-Token": rep_csrf},
        cookies=rep_cookies
    )
    assert self_verify.status_code == 400

    # Login Verifier 1 & verify
    v1_login = client.post("/api/auth/login", json={"email": "v1@example.com", "password": "password123"})
    v1_csrf = v1_login.json()["csrf_token"]
    v1_cookies = v1_login.cookies

    v1_verify = client.post(
        "/api/verifications",
        json={"issue_id": issue_id},
        headers={"X-CSRF-Token": v1_csrf},
        cookies=v1_cookies
    )
    assert v1_verify.status_code == 200

    # Try duplicate verification (should fail)
    v1_dup = client.post(
        "/api/verifications",
        json={"issue_id": issue_id},
        headers={"X-CSRF-Token": v1_csrf},
        cookies=v1_cookies
    )
    assert v1_dup.status_code == 400

    # Login Verifier 2 & verify (crosses threshold of 2)
    v2_login = client.post("/api/auth/login", json={"email": "v2@example.com", "password": "password123"})
    v2_csrf = v2_login.json()["csrf_token"]
    v2_cookies = v2_login.cookies

    v2_verify = client.post(
        "/api/verifications",
        json={"issue_id": issue_id},
        headers={"X-CSRF-Token": v2_csrf},
        cookies=v2_cookies
    )
    assert v2_verify.status_code == 200

    # Check escalation: Priority escalated to Medium, Department routed to Electricity Department
    escalated_issue = client.get(f"/api/issues/{issue_id}", cookies=v2_cookies)
    assert escalated_issue.json()["priority"] == "Medium"
    assert escalated_issue.json()["assigned_department"] == "Electricity Department"
