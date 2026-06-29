
def test_signup_and_login(client, db_session):
    # Signup Citizen
    response = client.post(
        "/api/auth/signup",
        json={
            "name": "Jane Citizen",
            "email": "jane@example.com",
            "password": "securepassword123",
            "role": "Citizen"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Jane Citizen"
    assert data["email"] == "jane@example.com"
    assert data["role"] == "Admin"  # First user becomes Admin automatically

    # Signup a second user (should stay Citizen)
    response2 = client.post(
        "/api/auth/signup",
        json={
            "name": "Bob Citizen",
            "email": "bob@example.com",
            "password": "securepassword123",
            "role": "Citizen"
        }
    )
    assert response2.status_code == 200
    assert response2.json()["role"] == "Citizen"

    # Login Citizen
    login_res = client.post(
        "/api/auth/login",
        json={
            "email": "bob@example.com",
            "password": "securepassword123"
        }
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "csrf_token" in login_data
    assert login_data["user"]["name"] == "Bob Citizen"

    # Failed login
    login_fail = client.post(
        "/api/auth/login",
        json={
            "email": "bob@example.com",
            "password": "wrongpassword"
        }
    )
    assert login_fail.status_code == 401

def test_rbac_access_control(client, db_session):
    # Register Citizen
    client.post(
        "/api/auth/signup",
        json={"name": "Admin User", "email": "admin@example.com", "password": "password123", "role": "Admin"}
    )
    client.post(
        "/api/auth/signup",
        json={"name": "Citizen User", "email": "citizen@example.com", "password": "password123", "role": "Citizen"}
    )

    # Login as Citizen
    login_res = client.post("/api/auth/login", json={"email": "citizen@example.com", "password": "password123"})
    csrf_token = login_res.json()["csrf_token"]
    cookies = login_res.cookies

    # Try to access Admin Audit trail - should return 403 Forbidden
    audit_res = client.get("/api/audit", cookies=cookies)
    assert audit_res.status_code == 403

    # Try to access Staff assignment - should return 403 Forbidden
    assign_res = client.post(
        "/api/departments/assign?issue_id=1&department=Electricity%20Department",
        headers={"X-CSRF-Token": csrf_token},
        cookies=cookies
    )
    assert assign_res.status_code == 403
