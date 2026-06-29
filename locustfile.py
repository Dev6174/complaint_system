# pyrefly: ignore [missing-import]
"""
Load test for the Complaint System API.

IMPORTANT: run setup_load_test_users.py once BEFORE this, to pre-create a
pool of test accounts. This avoids hammering the rate-limited
/api/auth/signup endpoint with one signup per simulated Locust user
(all Locust users share one IP, so signup would get rate-limited
almost immediately, cascading into 401s on every other endpoint).

Usage:
    python setup_load_test_users.py        # once
    locust -f locustfile.py --host http://127.0.0.1:5000

Then open http://localhost:8089 in your browser to start the test
and watch live charts (requests/sec, response times, failure rate).
"""
import random
from locust import HttpUser, task, between


class ComplaintSystemUser(HttpUser):
    # Each simulated user waits 1-3 seconds between actions —
    # mimics a real person clicking around, not a tight request loop.
    wait_time = between(1, 3)

    # Pool of pre-created accounts (see setup_load_test_users.py).
    NUM_TEST_USERS = 30
    PASSWORD = "LoadTest123!"

    def on_start(self):
        """Runs once per simulated user: log in with a random pooled account."""
        user_index = random.randint(0, self.NUM_TEST_USERS - 1)
        self.email = f"loadtest{user_index}@example.com"

        login_resp = self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.PASSWORD},
        )
        if login_resp.status_code != 200:
            print(
                f"[setup required] Login failed for {self.email} "
                f"({login_resp.status_code}). Run setup_load_test_users.py first."
            )

        csrf_resp = self.client.get("/api/auth/csrf")
        self.csrf_token = csrf_resp.json().get("csrf_token", "")

    @task(5)
    def view_issues(self):
        """Most common action: browsing the issue list."""
        self.client.get("/api/issues?limit=10")

    @task(3)
    def view_dashboard(self):
        """Second most common: checking the analytics dashboard (Redis-cached)."""
        self.client.get("/api/analytics/dashboard")

    @task(2)
    def view_leaderboard(self):
        self.client.get("/api/leaderboard")

    @task(1)
    def report_issue(self):
        """Least common but heaviest write: submitting a new issue."""
        self.client.post(
            "/api/issues",
            data={
                "title": "Load test pothole report",
                "description": "Automatically generated issue for load testing purposes.",
                "category": "Potholes",
                "priority": "Low",
                "latitude": "28.6139",
                "longitude": "77.2090",
            },
            headers={"X-CSRF-Token": self.csrf_token},
        )
