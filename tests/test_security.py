from io import BytesIO


def test_csrf_protection(client, db_session):
    # Setup user
    client.post("/api/auth/signup", json={"name": "Alice", "email": "alice@example.com", "password": "password123", "role": "Citizen"})
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    cookies = login_res.cookies

    # State changing POST request without X-CSRF-Token header -> should fail with 403
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
        cookies=cookies
    )
    assert report_res.status_code == 403

def test_input_validation(client, db_session):
    client.post("/api/auth/signup", json={"name": "Alice", "email": "alice@example.com", "password": "password123", "role": "Citizen"})
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    csrf_token = login_res.json()["csrf_token"]
    cookies = login_res.cookies

    # Latitude out of bounds -> should fail with 422 (Pydantic validation) or 400
    res = client.post(
        "/api/issues",
        data={
            "title": "Severe pothole",
            "description": "Deep pothole causing road bumps.",
            "category": "Potholes",
            "priority": "Medium",
            "latitude": 95.0, # invalid
            "longitude": -74.0060
        },
        headers={"X-CSRF-Token": csrf_token},
        cookies=cookies
    )
    assert res.status_code in [400, 422]

def test_file_upload_security(client, db_session):
    client.post("/api/auth/signup", json={"name": "Alice", "email": "alice@example.com", "password": "password123", "role": "Citizen"})
    login_res = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    csrf_token = login_res.json()["csrf_token"]
    cookies = login_res.cookies

    # Try uploading a disallowed shell script masked as image extension
    bad_file = BytesIO(b"#!/usr/bin/env python\nprint('hello')")

    res = client.post(
        "/api/issues",
        data={
            "title": "Severe pothole near street corner",
            "description": "Deep pothole causing road bumps and hazard to vehicles.",
            "category": "Potholes",
            "priority": "Medium",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        files={"file": ("malicious.jpg", bad_file, "image/jpeg")}, # jpg but starts with script content
        headers={"X-CSRF-Token": csrf_token},
        cookies=cookies
    )
    # Magic bytes check in server should reject this and return 400 Bad Request
    assert res.status_code == 400
    assert "Invalid JPEG file headers" in res.json()["detail"]
