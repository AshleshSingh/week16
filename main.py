import os
import re
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from jose import jwt, JWTError

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scheduler.db")
SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="AI Scheduler OS Prototype")
app.mount("/static", StaticFiles(directory="static"), name="static")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, index=True)
    title = Column(String)
    category = Column(String)
    color = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    priority = Column(String, default="medium")
    reminder_minutes = Column(Integer, default=30)
    location = Column(String, default="")
    notes = Column(Text, default="")
    is_private = Column(Boolean, default=False)


class BookingRequest(Base):
    __tablename__ = "booking_requests"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, index=True)
    guest_name = Column(String)
    guest_email = Column(String)
    requested_start = Column(DateTime)
    requested_end = Column(DateTime)
    purpose = Column(String)
    status = Column(String, default="pending")


Base.metadata.create_all(bind=engine)


class LoginRequest(BaseModel):
    email: str
    password: str


class EventCreate(BaseModel):
    title: str
    category: str = "Personal"
    color: str = "#10b981"
    start_time: datetime
    end_time: datetime
    priority: str = "medium"
    reminder_minutes: int = 30
    location: str = ""
    notes: str = ""
    is_private: bool = False


class ChatRequest(BaseModel):
    message: str


class IngestRequest(BaseModel):
    source_type: str
    content: str


class BookingCreate(BaseModel):
    guest_name: str
    guest_email: str
    requested_start: datetime
    requested_end: datetime
    purpose: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(password, password_hash):
    return pwd_context.verify(password, password_hash)


def create_token(user: User):
    payload = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(token: str = "", db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user), "user": {"name": user.name, "email": user.email, "tenant_id": user.tenant_id}}


@app.get("/api/events")
def list_events(token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    events = db.query(Event).filter(Event.tenant_id == user.tenant_id).order_by(Event.start_time).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "category": e.category,
            "color": e.color,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
            "priority": e.priority,
            "reminder_minutes": e.reminder_minutes,
            "location": e.location,
            "notes": e.notes,
            "is_private": e.is_private,
        }
        for e in events
    ]


@app.post("/api/events")
def create_event(req: EventCreate, token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    event = Event(tenant_id=user.tenant_id, **req.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"status": "created", "id": event.id}


@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    event = db.query(Event).filter(Event.id == event_id, Event.tenant_id == user.tenant_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"status": "deleted"}


def category_for_text(text: str):
    t = text.lower()
    if any(x in t for x in ["client", "project", "standup", "review", "workshop", "architecture"]):
        return "Work", "#3b82f6"
    if any(x in t for x in ["doctor", "gym", "health", "medicine"]):
        return "Health", "#ef4444"
    if any(x in t for x in ["family", "wife", "dinner", "birthday"]):
        return "Family", "#f59e0b"
    if any(x in t for x in ["friend", "coffee", "party"]):
        return "Friends", "#8b5cf6"
    return "Personal", "#10b981"


def mock_extract_event(content: str):
    category, color = category_for_text(content)
    now = datetime.now()
    hour_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", content.lower())
    start = now.replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    if hour_match:
        hour = int(hour_match.group(1))
        minute = int(hour_match.group(2) or 0)
        ampm = hour_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        start = start.replace(hour=hour, minute=minute)
    else:
        start = start.replace(hour=10)

    duration = 60
    if "30 min" in content.lower():
        duration = 30
    if "2 hour" in content.lower():
        duration = 120

    title = content.strip().split("\n")[0][:80]
    title = re.sub(r"^(subject:|re:|fw:)\s*", "", title, flags=re.I) or "AI extracted event"

    priority = "high" if any(x in content.lower() for x in ["urgent", "important", "critical"]) else "medium"

    return {
        "title": title,
        "category": category,
        "color": color,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(minutes=duration)).isoformat(),
        "priority": priority,
        "reminder_minutes": 30 if priority == "medium" else 60,
        "location": "TBD",
        "notes": content[:500],
        "confidence": 0.82,
        "summary": "Prototype AI extracted a schedulable event from the supplied content."
    }


@app.post("/api/ingest")
def ingest(req: IngestRequest, token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    extracted = mock_extract_event(req.content)
    event = Event(
        tenant_id=user.tenant_id,
        title=extracted["title"],
        category=extracted["category"],
        color=extracted["color"],
        start_time=datetime.fromisoformat(extracted["start_time"]),
        end_time=datetime.fromisoformat(extracted["end_time"]),
        priority=extracted["priority"],
        reminder_minutes=extracted["reminder_minutes"],
        location=extracted["location"],
        notes=extracted["notes"],
    )
    db.add(event)
    db.commit()
    return {"status": "event_created_from_ingestion", "extracted": extracted}


@app.post("/api/chat")
def chat(req: ChatRequest, token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    events = db.query(Event).filter(Event.tenant_id == user.tenant_id).all()
    msg = req.message.lower()

    if "free" in msg or "available" in msg:
        return {"reply": "Your best open slots appear to be tomorrow 10:00 AM–11:00 AM and 3:00 PM–4:00 PM. I recommend 10:00 AM for focused scheduling."}

    if "busy" in msg:
        busiest = max(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], key=lambda _: len(events))
        return {"reply": f"You currently have {len(events)} events. Your schedule density is highest around mid-week. Consider protecting a focus block."}

    if "family" in msg or "dinner" in msg:
        return {"reply": "I can schedule a family block in the evening. Suggested slot: Saturday 7:00 PM–9:00 PM with a 60-minute reminder."}

    return {"reply": "I can help create, search, modify, and optimize your schedule. Try asking: 'Find my free slots tomorrow' or paste a meeting note into the Ingest Center."}


@app.get("/api/availability")
def availability(db: Session = Depends(get_db)):
    tenant_id = "tenant-demo"
    events = db.query(Event).filter(Event.tenant_id == tenant_id).all()
    today = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    slots = []
    for d in range(5):
        day = today + timedelta(days=d)
        for h in [9, 10, 11, 14, 15, 16]:
            start = day.replace(hour=h)
            end = start + timedelta(hours=1)
            busy = any(e.start_time < end and e.end_time > start for e in events)
            slots.append({
                "start": start.isoformat(),
                "end": end.isoformat(),
                "status": "unavailable" if busy else "free"
            })
    return slots


@app.post("/api/booking-request")
def booking_request(req: BookingCreate, db: Session = Depends(get_db)):
    br = BookingRequest(
        tenant_id="tenant-demo",
        guest_name=req.guest_name,
        guest_email=req.guest_email,
        requested_start=req.requested_start,
        requested_end=req.requested_end,
        purpose=req.purpose,
        status="pending"
    )
    db.add(br)
    db.commit()
    return {"status": "request_submitted", "message": "Your calendar block request has been sent for approval."}


@app.get("/api/booking-requests")
def booking_requests(token: str, db: Session = Depends(get_db)):
    user = current_user(token, db)
    reqs = db.query(BookingRequest).filter(BookingRequest.tenant_id == user.tenant_id).order_by(BookingRequest.id.desc()).all()
    return [
        {
            "id": r.id,
            "guest_name": r.guest_name,
            "guest_email": r.guest_email,
            "requested_start": r.requested_start.isoformat(),
            "requested_end": r.requested_end.isoformat(),
            "purpose": r.purpose,
            "status": r.status
        }
        for r in reqs
    ]
