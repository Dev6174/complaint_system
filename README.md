# Complaint System

A full-stack complaint management platform built with **FastAPI** that allows citizens to report community issues, upload evidence, and track the progress of their complaints. The system also provides moderation tools, department management, analytics, and AI-assisted complaint categorisation.

This project was built with a focus on security, maintainability, and real-world backend practices rather than just implementing CRUD operations.

---

## Features

- User authentication using JWT
- Role-based access control (Citizen, Moderator, Department, Admin)
- Create, update and track complaints
- Secure file uploads
- AI-assisted complaint categorisation
- Complaint verification workflow
- Department assignment
- Analytics and reporting
- Citizen leaderboard
- Audit logging
- Prometheus metrics
- Sentry integration

---

## Tech Stack

**Backend**
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

**Frontend**
- HTML
- CSS
- JavaScript
- Leaflet.js

**Database**
- SQLite

**Security**
- JWT Authentication
- bcrypt password hashing
- CSRF protection
- IDOR prevention
- Secure file validation

---

## Getting Started

### Clone the repository

```bash
git clone https://github.com/Dev6174/complaint_system.git

cd complaint_system
```

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate it

Windows

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=sqlite:///./complaint_system.db

SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

AI_CLASSIFIER_ENDPOINT=https://api.example.com/classify
AI_CLASSIFIER_API_KEY=your-api-key

VERIFICATION_THRESHOLD=5
```

---

## Running the project

Start the development server:

```bash
uvicorn app.main:app --reload
```

The application will be available at:

```
http://127.0.0.1:8000
```

API documentation:

```
http://127.0.0.1:8000/docs
```

---

## Running tests

```bash
pytest
```

The test suite covers authentication, RBAC, complaint APIs, upload security, AI fallback behaviour and verification workflows.

---

## Project Structure

```text
app/
├── routers/
├── services/
├── middleware/
├── observability/
├── templates/
├── static/
└── main.py

tests/
migrations/
uploads/
```

---

## Screenshots

### Dashboard

_Add screenshot_

### Complaint Portal

_Add screenshot_

### API Documentation

_Add screenshot_

---

## Future Improvements

- PostgreSQL support
- Docker deployment
- Redis caching
- Email notifications
- Real-time updates
- Mobile application

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.