# Complaint System

A production-grade, full-stack web application designed for citizens to report local community issues, have them verified, assign departments, and track resolution metrics, backed by a gamified citizen-engagement system.

---

## 1. Prerequisites & Environment Setup

This project is built using Python 3.13 and SQLite.

### Local Installation

1. **Clone/extract the project** into your workspace.
2. **Create the virtual environment**:
   ```bash
   python -m venv .venv
   ```
3. **Activate the virtual environment**:
   - **Windows PowerShell**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Git Bash / Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```
4. **Install all required dependencies**:
   ```bash
   .venv\Scripts\pip install -r requirements.txt
   ```

---

## 2. Configuration Settings (`.env`)

Create a `.env` file in the root directory (a `.env.example` has been provided for reference). The application accepts the following environment variables:

```ini
# Database URL
DATABASE_URL=sqlite:///./complaint_system.db

# JWT Security
SECRET_KEY=super-secret-dev-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# External AI Classification Service
AI_CLASSIFIER_ENDPOINT=https://api.external-categorization.local/classify
AI_CLASSIFIER_API_KEY=mock-api-key-here

# Verification settings
VERIFICATION_THRESHOLD=5
```

---

## 3. Running the Application

To launch the FastAPI server, run:

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open your browser and navigate to **`http://127.0.0.1:8000`** to access the Smart Citizen Portal.

---

## 4. Running the Tests

To execute the automated unit and integration tests (testing Auth, RBAC, IDOR, AI Fallback, and Upload Security), run:

```bash
.venv\Scripts\pytest -v
```

---

## 5. System Design Details

- **Backend Stack**: Built on **FastAPI** for high performance, utilizing **SQLAlchemy** for database parameterization and **Pydantic** for schemas.
- **Frontend SPA**: Handled as a Single-Page Application using vanilla **HTML5**, **ES6 JavaScript**, and **CSS3 variables** (implementing a modern dark-mode glassmorphic interface). Mapping features utilize **Leaflet.js**.
- **Security First**: Employs double-submit cookie CSRF validation, bcrypt hashing, object-level check authorizations, magic-byte upload filtering, and structured immutable audit logging.
