# Threat Model — Complaint System

This document outlines the security risk assessment, threat vectors considered, and mitigations implemented in the **Complaint System** application.

---

## 1. Threat Mitigation Matrix

| Threat Category | Potential Impact | Code-level Mitigation Implemented |
| :--- | :--- | :--- |
| **SQL Injection (SQLi)** | Data leaks, complete database takeover. | Parameterized queries enforced globally via SQLAlchemy ORM. Raw string concatenation is prohibited. |
| **Insecure Direct Object References (IDOR)** | Users modifying other citizens' issues or feedback ratings. | Ownership authorization checks matching `issue.reporter_id == current_user.id` before edits/updates. Staff role validation for resolution dispatches. |
| **Cross-Site Request Forgery (CSRF)** | Attacker tricking a citizen's session into reporting fake issues. | Double-Submit Cookie Pattern. A signed CSRF token cookie is set at login. The frontend must extract and include this in the `X-CSRF-Token` header on POST/PUT/DELETE requests. |
| **Cross-Site Scripting (XSS)** | Session theft, UI defacement. | 1. Input sanitization in schemas.<br>2. Contextual escaping (using safe DOM APIs like `.textContent` in `app.js`).<br>3. Enforcement of a strict Content Security Policy (CSP) header. |
| **Malicious File Upload / Remote Code Execution (RCE)** | Upload of scripts (`.php`/`.py` / executables) executing on server. | 1. Extension allow-list (`.jpg`, `.jpeg`, `.png`, `.webp`, `.mp4`).<br>2. Size restriction (10MB checked before buffering).<br>3. Magic bytes validation to verify headers match extension type.<br>4. Re-naming to random UUIDs and storage outside executable web paths. |
| **Credential Brute-Forcing** | Account takeover. | 1. Passwords hashed using bcrypt slow-hashing.<br>2. Local sliding-window rate-limiting on login (`/api/auth/login`) locking IPs and emails after 5 failed attempts. |
| **Tampering & Audit Deficiencies** | Staff covering up mistakes, untracked changes. | Immutable `audit_logs` database table. All state modifications (logins, creations, escalations, assignments, resolutions) write to this table via append-only logs. |

---

## 2. Security Headers Enforced

The application injects the following security headers via middleware on all HTTP responses:

- `X-Content-Type-Options: nosniff`: Prevents browsers from MIME-sniffing file content types (critical for secure file uploads).
- `X-Frame-Options: DENY`: Protects against Clickjacking.
- `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes metadata exposure.
- `Content-Security-Policy`: Restricts scripts, style sheets, tiles, and connection sources to safe domains only:
  ```text
  default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self';
  ```
