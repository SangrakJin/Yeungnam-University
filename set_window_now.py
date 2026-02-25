from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import ApplicationWindow
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

def main():
    db = SessionLocal()
    try:
        win = db.query(ApplicationWindow).first()
        if not win:
            raise SystemExit("No application_window row found. Start server once to seed DB.")
        now = datetime.utcnow()  # naive UTC
        win.start_at = now - timedelta(minutes=5)
        win.end_at = now + timedelta(days=1)
        win.is_enabled = True
        db.commit()
        print("OK: window updated to open now (UTC naive).")
        print("start_at(UTC):", win.start_at)
        print("end_at(UTC):", win.end_at)
    finally:
        db.close()

if __name__ == "__main__":
    main()