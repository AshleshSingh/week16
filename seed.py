from datetime import datetime, timedelta
from main import SessionLocal, User, Event, BookingRequest, pwd_context, Base, engine

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter(User.email == "ashlesh@example.com").first():
    user = User(
        tenant_id="tenant-demo",
        name="Ashlesh Singh",
        email="ashlesh@example.com",
        password_hash=pwd_context.hash("demo123"),
        role="owner"
    )
    db.add(user)

categories = {
    "Work": "#3b82f6",
    "Personal": "#10b981",
    "Family": "#f59e0b",
    "Friends": "#8b5cf6",
    "Health": "#ef4444",
    "Finance": "#06b6d4",
    "Travel": "#6366f1",
    "Learning": "#f97316",
}

sample_events = [
    ("Architecture Review - AI Scheduler", "Work", 1, 10, 60, "Review prototype architecture and deployment plan."),
    ("Family Dinner", "Family", 1, 19, 120, "Dinner block with family."),
    ("Gym + Walk", "Health", 2, 7, 60, "Health routine."),
    ("Coffee with Friend", "Friends", 2, 17, 60, "Catch up over coffee."),
    ("Project Deep Work", "Work", 3, 9, 120, "Focus block for solution design."),
    ("Finance Bill Reminder", "Finance", 3, 18, 30, "Pay monthly bills."),
    ("Learning Block - Agentic Apps", "Learning", 4, 20, 60, "Study agentic coding patterns."),
    ("Travel Planning", "Travel", 5, 11, 60, "Plan upcoming family trip."),
]

for title, category, day_offset, hour, minutes, notes in sample_events:
    exists = db.query(Event).filter(Event.title == title).first()
    if not exists:
        start = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        db.add(Event(
            tenant_id="tenant-demo",
            title=title,
            category=category,
            color=categories[category],
            start_time=start,
            end_time=start + timedelta(minutes=minutes),
            priority="high" if category == "Work" else "medium",
            reminder_minutes=30,
            location="TBD",
            notes=notes,
            is_private=category in ["Family", "Health", "Finance"]
        ))

if not db.query(BookingRequest).first():
    db.add(BookingRequest(
        tenant_id="tenant-demo",
        guest_name="Guest User",
        guest_email="guest@example.com",
        requested_start=datetime.now().replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=2),
        requested_end=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=2),
        purpose="Prototype guest booking request",
        status="pending"
    ))

db.commit()
db.close()
print("Seed complete. Login: ashlesh@example.com / demo123")
