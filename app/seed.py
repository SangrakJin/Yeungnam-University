from sqlalchemy.orm import Session
from .models import Professor, ApplicationWindow
from .services import kst_str_to_utc

PROFESSORS = [
    "김종주 교수님",
    "백광현 교수님",
    "전준현 교수님",
    "최정규 교수님",
    "진상락 교수님",
]

def seed_if_needed(db: Session):
    if db.query(Professor).count() == 0:
        for name in PROFESSORS:
            db.add(Professor(name=name, base_capacity=12, extra_capacity=0, active=True))

    win = db.query(ApplicationWindow).first()
    if not win:
        start_utc = kst_str_to_utc("2026-02-25 20:15")
        end_utc = kst_str_to_utc("2026-03-13 18:00")
        db.add(ApplicationWindow(start_at=start_utc, end_at=end_utc, is_enabled=True))

    db.commit()