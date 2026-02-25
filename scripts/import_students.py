import csv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import AllowedStudent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

def main(csv_path: str):
    engine = create_engine(
        DATABASE_URL,
        future=True,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        upserted = 0
        for r in rows:
            student_no = (r.get("student_no") or "").strip()
            name = (r.get("name") or "").strip()
            if not student_no or not name:
                continue
            existing = db.query(AllowedStudent).filter(AllowedStudent.student_no == student_no).first()
            if not existing:
                db.add(AllowedStudent(student_no=student_no, name=name))
            else:
                existing.name = name
            upserted += 1

        db.commit()
        print(f"OK: upserted {upserted} students into allowed_students")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_students.py students.csv")
        raise SystemExit(1)
    main(sys.argv[1])