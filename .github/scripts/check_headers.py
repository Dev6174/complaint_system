"""
CI script: verify required security headers are present on HTTP responses.
Fails with exit code 1 if any required header is missing or has wrong value.
Run after the server is started in the CI workflow.
"""
import sys
import urllib.request

BASE_URL = "http://127.0.0.1:5000"

REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "strict-transport-security": "max-age=63072000; includeSubDomains",
}

CSP_REQUIRED_DIRECTIVES = [
    "default-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
]

def check(url: str) -> bool:
    print(f"\nChecking: {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except Exception as e:
        print(f"  ERROR: Could not reach {url} — {e}")
        return False

    passed = True

    for header, expected_value in REQUIRED_HEADERS.items():
        actual = headers.get(header, "")
        if expected_value.lower() in actual.lower():
            print(f"  ✅ {header}: {actual}")
        else:
            print(f"  ❌ {header}: expected '{expected_value}', got '{actual}'")
            passed = False

    csp = headers.get("content-security-policy", "")
    for directive in CSP_REQUIRED_DIRECTIVES:
        if directive in csp:
            print(f"  ✅ CSP has: {directive}")
        else:
            print(f"  ❌ CSP missing: {directive}")
            passed = False

    if "unsafe-eval" in csp:
        print(f"  ❌ CSP contains 'unsafe-eval' — must be removed")
        passed = False
    else:
        print(f"  ✅ CSP does not contain 'unsafe-eval'")

    return passed


def main():
    endpoints = [
        f"{BASE_URL}/api/auth/csrf",   # Auth endpoint
        f"{BASE_URL}/docs",            # Swagger — should have scoped CSP
    ]

    all_passed = all(check(url) for url in endpoints)

    print("\n" + ("=" * 50))
    if all_passed:
        print("✅ All security header checks passed.")
        sys.exit(0)
    else:
        print("❌ One or more security header checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
