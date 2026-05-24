# AI Scheduler OS - Render Prototype

A working AI-native personal scheduler prototype.

## What this includes

- FastAPI backend
- Static premium frontend
- SQLite database with seeded sample data
- Email/password login
- User mode
- Guest availability mode
- AI-style scheduler bot with mock intelligence
- Ingestion from pasted email/PDF/note text
- Event creation
- Reminder/color/category model
- Render-ready deployment

## Prototype Login

```text
Email: ashlesh@example.com
Password: demo123
```

## Local Run

```bash
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```

## Render Deployment

Render settings:

```text
Language: Python 3
Build Command: pip install -r requirements.txt && python seed.py
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Environment Variables

Required for prototype:

```text
APP_SECRET_KEY=change-this-secret
```

Optional:

```text
OPENAI_API_KEY=
GROQ_API_KEY=
```

If no AI keys are provided, the app uses deterministic mock AI logic.
