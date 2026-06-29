# pyrefly: ignore [missing-import]
"""
Run this ONCE before load testing to pre-create a pool of test user accounts.
This avoids hammering the rate-limited /api/auth/signup endpoint with one
signup per simulated Locust user.

Usage:
    python setup_load_test_users.py
"""
import time
import requests

BASE_URL = "http://127.0.0.1:5000"
NUM_USERS = 30
PASSWORD = "LoadTest123!"

print(f"Creating {NUM_USERS} test users (this respects rate limits, so it's slow on purpose)...")

created = 0
i = 0
while i < NUM_USERS:
    email = f"loadtest{i}@example.com"
    resp = requests.post(
        f"{BASE_URL}/api/auth/signup",
        json={
            "name": f"Load Test {i}",
            "email": email,
            "password": PASSWORD,
            "role": "Citizen",
        },
    )
    if resp.status_code == 200:
        created += 1
        print(f"  [{i+1}/{NUM_USERS}] created {email}")
    elif resp.status_code == 400:
        # Already exists from a previous run — fine, treat as success
        created += 1
        print(f"  [{i+1}/{NUM_USERS}] {email} already exists, skipping")
    elif resp.status_code == 429:
        print(f"  [{i+1}/{NUM_USERS}] rate limited, waiting 12s...")
        time.sleep(12)
        continue  # retry this same i, don't increment
    else:
        print(f"  [{i+1}/{NUM_USERS}] unexpected status {resp.status_code}: {resp.text}")

    time.sleep(0.5)  # stay comfortably under the 5/min signup limit
    i += 1

print(f"\nDone. {created}/{NUM_USERS} test users ready (loadtest0..{NUM_USERS-1}@example.com / {PASSWORD})")
