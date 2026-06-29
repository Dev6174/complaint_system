# Build Prompt — "Complaint System"

Build a production-grade, full-stack web application named **Complaint System**.

## 1. Purpose

Complaint System lets citizens report local community issues (potholes, water leakage,
damaged streetlights, waste management, infrastructure problems, public safety hazards,
etc.), have them verified by other community members, route them to the correct
department, track their status in real time, and measure resolution impact — all with
gamified citizen engagement and data-driven dashboards.

## 2. Core Functional Requirements

### 2.1 Identity & Roles
- Three roles: **Citizen**, **Staff** (department agent), **Admin**.
- Secure registration and login for all roles.
- Role-based access control (RBAC) enforced on every server-side action, not just hidden
  in the UI.
- Profile management (name, email, mobile, password change).

### 2.2 Issue Reporting
- Citizens submit issues with: title, description, category, priority, photo and/or
  video attachment, and geo-location (latitude/longitude, picked on a map or via device
  location).
- Server-side automated categorization and priority suggestion: integrate with a
  configurable external AI classification API (endpoint and key supplied via
  environment configuration) that takes the title, description, and optional image and
  returns a suggested category, priority, confidence score, and short reasoning. If the
  service is slow, unavailable, or returns an error, fall back automatically to a
  built-in rule/keyword-based classifier so the feature always degrades gracefully and
  never blocks submission. Do not name the underlying AI provider anywhere in code,
  UI copy, or documentation — refer to it only as the "automated categorization
  service."
- Citizens may always override the suggested category/priority before submitting.

### 2.3 Community Verification
- Other citizens (not the original reporter) can verify/confirm an issue.
- Track a verification count per issue; once it crosses a configurable threshold,
  automatically escalate priority and notify the assigned department.
- Prevent duplicate verification by the same user and self-verification by the reporter.

### 2.4 Tracking & Resolution
- Full status lifecycle: Open → In Progress → Resolved → Closed, plus Reopened.
- Status history with timestamps, visible to the reporter and staff.
- Department assignment and staff resolution workflow, with resolution notes and
  resolution date recorded.
- Search and sort by ID, priority, date, status, and category, with pagination for
  large result sets.

### 2.5 Feedback
- Citizens rate resolved issues (1–5) and leave comments.
- Feedback feeds into department/staff performance views.

### 2.6 Notifications
- In-app notifications for status changes, verification milestones, and resolution,
  tied to the correct recipient (not broadcast to everyone).

### 2.7 Gamification
- Points awarded for reporting, verifying, and leaving feedback; bonus points when a
  reported issue is resolved.
- Badges for engagement milestones.
- A public leaderboard.

### 2.8 Dashboards & Insights
- Impact dashboard: counts by status/category/priority, map view of all open issues,
  resolution-rate trends.
- Predictive insight: estimate expected resolution time for a new issue from historical
  averages by category and priority, and flag "at risk" issues (old + high priority +
  still open).
- Exportable reports (CSV) for summary, pending, resolved, department, and feedback
  views.

### 2.9 Audit Trail
- Every state-changing action (registration, status update, assignment, resolution,
  verification) is recorded in an immutable, timestamped activity log visible to admins
  for transparency and accountability.

## 3. Security Requirements — target zero known vulnerabilities

- **Input validation**: validate and sanitize every input server-side (type, length,
  format, allowed values); never trust client-side validation alone.
- **Injection prevention**: use parameterized queries or an ORM exclusively; no raw
  string-concatenated SQL anywhere.
- **Authentication**: passwords hashed with a strong, salted, slow hash (e.g.
  bcrypt/argon2-class algorithm); no plaintext or reversible storage; account lockout /
  backoff after repeated failed logins; secure password-reset flow with expiring,
  single-use tokens.
- **Session management**: signed, httpOnly, SameSite, Secure cookies or short-lived
  tokens with refresh/rotation; session invalidation on logout and password change.
- **Authorization**: enforce object-level ownership checks on every request that
  references an ID (no IDOR — a user must not be able to view/edit another user's data
  by guessing or changing an ID).
- **CSRF protection** on all state-changing requests.
- **XSS prevention**: contextual output encoding everywhere user content is rendered;
  a strict Content-Security-Policy; no unsanitized HTML injection.
- **File upload security**: enforce allow-lists on MIME type and extension, strict size
  limits, randomized non-guessable storage filenames, storage outside any directly
  executable web path, and rejection of executable/script file types; scan uploads
  before serving them back.
- **Secrets management**: all API keys, database credentials, and signing secrets come
  from environment variables or a secrets manager — never hardcoded, never committed,
  with a checked-in `.env.example` containing only placeholder values.
- **Transport security**: enforce HTTPS/TLS everywhere, HSTS enabled, no mixed content.
- **Security headers**: X-Content-Type-Options, X-Frame-Options (or frame-ancestors),
  Referrer-Policy, and a restrictive CSP on all responses.
- **Rate limiting & throttling**: per-IP and per-account limits on login, registration,
  issue submission, and any call to the external categorization service, to prevent
  brute force and abuse.
- **Error handling**: generic error responses to clients; full details only in
  server-side logs, never in stack traces shown to users.
- **Logging**: structured, centralized logs that exclude passwords, tokens, and other
  secrets/PII; the audit trail (section 2.9) is append-only.
- **Dependency hygiene**: pin dependency versions, run automated vulnerability scanning
  in CI, and document a process for prompt patching.
- **Automated security testing**: include unit/integration tests that specifically
  cover authz boundaries, input validation edge cases, and upload restrictions.

## 4. Load Handling & Scalability Requirements

- Stateless application layer so multiple instances can run behind a load balancer.
- Connection pooling and indexed queries on all frequently filtered/sorted columns
  (status, category, priority, user ID, department ID); pagination on every list
  endpoint — never return unbounded result sets.
- Caching for expensive aggregate/dashboard queries, with sensible invalidation on
  writes.
- Background/async processing for slow operations (external categorization calls,
  media processing, report generation, notification fan-out) so request threads are
  never blocked; apply timeouts and a circuit-breaker so a slow external dependency
  cannot cascade into an outage.
- Efficient, size-limited, streamed media uploads; large media offloaded to object
  storage rather than the application server's local disk.
- Health-check endpoint and basic metrics/observability (request latency, error rate,
  queue depth) suitable for autoscaling decisions.
- Define and document expected load targets and include a basic load test before
  considering the system production-ready.

## 5. Engineering Deliverables

- Clean, modular architecture with clear separation between API/controllers, business
  logic, and data access.
- Automated test suite (unit + integration), including the security-focused tests in
  section 3.
- `README.md` covering setup, configuration (all required environment variables with
  placeholder examples), and how to run tests.
- A short threat-model summary documenting the main risks considered and how each is
  mitigated.
- Use "Complaint System" as the project name consistently in code, configuration,
  documentation, and UI — do not reference any AI vendor or model name anywhere in the
  project.
