# FastAPI
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from starlette.responses import StreamingResponse

# 표준 라이브러리
import io
import csv
import os
import random

# SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy import select, func

# 내부 모듈
from .database import Base, engine, get_db
from .models import AllowedStudent, User, SessionToken, Professor, Selection, ApplicationWindow
from .schemas import (
    StartSessionReq, StartSessionRes, WindowRes,
    ProfessorsRes, ProfessorCard, SelectReq, MySelectionRes,
    AdminAddSeatReq, AdminAssignReq, AdminDashboardRes, AdminDashboardItem
)
from .security import new_token, expiry_utc, require_admin_key
from .services import TITLE, now_utc, utc_to_kst_str, is_window_open
from .seed import seed_if_needed

app = FastAPI(title="Advisor Allocation API", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    from .database import SessionLocal
    db = SessionLocal()
    try:
        seed_if_needed(db)
    finally:
        db.close()

def get_window(db: Session) -> ApplicationWindow:
    win = db.query(ApplicationWindow).first()
    if not win:
        raise HTTPException(status_code=500, detail="application window not initialized")
    return win

def get_session_user(db: Session, authorization: str | None) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    sess = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not sess:
        raise HTTPException(status_code=401, detail="invalid token")
    if sess.expires_at < now_utc():
        raise HTTPException(status_code=401, detail="token expired")
    user = db.query(User).filter(User.id == sess.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user

def window_response(win: ApplicationWindow) -> WindowRes:
    n = now_utc()
    open_now = is_window_open(n, win.start_at, win.end_at, win.is_enabled)
    return WindowRes(
        start_at_kst=utc_to_kst_str(win.start_at),
        end_at_kst=utc_to_kst_str(win.end_at),
        is_enabled=win.is_enabled,
        is_open_now=open_now,
        now_kst=utc_to_kst_str(n),
    )

@app.get("/window", response_model=WindowRes)
def read_window(db: Session = Depends(get_db)):
    return window_response(get_window(db))

@app.post("/session/start", response_model=StartSessionRes)
def start_session(payload: StartSessionReq, db: Session = Depends(get_db)):
    allowed = db.query(AllowedStudent).filter(AllowedStudent.student_no == payload.student_no).first()
    if not allowed:
        raise HTTPException(status_code=403, detail="등록되지 않은 학생입니다")
    if allowed.name.strip() != payload.name.strip():
        raise HTTPException(status_code=403, detail="학번-이름이 일치하지 않습니다")

    user = db.query(User).filter(User.student_no == payload.student_no).first()
    if not user:
        user = User(student_no=payload.student_no, name=payload.name.strip())
        db.add(user)
        db.flush()
    else:
        if user.name != payload.name.strip():
            user.name = payload.name.strip()

    token = new_token()
    exp = expiry_utc()
    db.add(SessionToken(token=token, user_id=user.id, expires_at=exp))
    db.commit()
    return StartSessionRes(token=token, expires_at=exp)

@app.get("/professors", response_model=ProfessorsRes)
def list_professors(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _ = get_session_user(db, authorization)

    professors = db.query(Professor).filter(Professor.active == True).order_by(Professor.id.asc()).all()

    student_counts = dict(
        db.query(Selection.professor_id, func.count(Selection.id))
          .filter(Selection.method == "student")
          .group_by(Selection.professor_id)
          .all()
    )
    total_counts = dict(
        db.query(Selection.professor_id, func.count(Selection.id))
          .group_by(Selection.professor_id)
          .all()
    )

    cards = []
    for p in professors:
        sc = int(student_counts.get(p.id, 0))
        tc = int(total_counts.get(p.id, 0))
        is_full = sc >= p.base_capacity
        cards.append(ProfessorCard(
            id=p.id,
            name=p.name,
            student_count=sc,
            base_capacity=p.base_capacity,
            is_full=is_full,
            full_message=("해당 교수님 정원마감" if is_full else None),
            total_count=tc,
            total_capacity=p.base_capacity + p.extra_capacity,
        ))
    return ProfessorsRes(title=TITLE, professors=cards)

@app.get("/my-selection", response_model=MySelectionRes)
def my_selection(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    user = get_session_user(db, authorization)
    sel = db.query(Selection).filter(Selection.user_id == user.id).first()
    if not sel:
        return MySelectionRes(student_no=user.student_no, name=user.name)
    prof = db.query(Professor).filter(Professor.id == sel.professor_id).first()
    return MySelectionRes(
        student_no=user.student_no, name=user.name,
        professor_id=sel.professor_id,
        professor_name=(prof.name if prof else None),
        method=sel.method,
    )

# ✅✅✅ [추가] 내 선택 초기화(삭제) 엔드포인트: DELETE /my-selection
@app.delete("/my-selection")
def reset_my_selection(db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    user = get_session_user(db, authorization)

    sel = db.query(Selection).filter(Selection.user_id == user.id).first()
    if not sel:
        # 이미 비어있으면 그냥 OK
        return {"ok": True, "deleted": False}

    db.delete(sel)
    db.commit()
    return {"ok": True, "deleted": True}

@app.post("/select", response_model=MySelectionRes)
def select_professor(payload: SelectReq, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    user = get_session_user(db, authorization)
    win = get_window(db)

    if not is_window_open(now_utc(), win.start_at, win.end_at, win.is_enabled):
        raise HTTPException(status_code=403, detail="신청기간이 아닙니다")

    # 교수 조회 (SQLite에서는 with_for_update 생략)
    stmt = select(Professor).where(Professor.id == payload.professor_id)
    if engine.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    target = db.execute(stmt).scalar_one_or_none()

    if not target or not target.active:
        raise HTTPException(status_code=404, detail="교수를 찾을 수 없습니다")

    current = db.query(Selection).filter(Selection.user_id == user.id).first()

    # 학생 선착순 카운트 (student method만)
    q = db.query(func.count(Selection.id)).filter(
        Selection.professor_id == target.id,
        Selection.method == "student",
    )
    if current:
        q = q.filter(Selection.user_id != user.id)
    student_count = int(q.scalar() or 0)

    if student_count >= target.base_capacity:
        raise HTTPException(status_code=409, detail="해당 교수님 정원마감")

    if not current:
        db.add(Selection(user_id=user.id, professor_id=target.id, method="student"))
    else:
        current.professor_id = target.id
        current.method = "student"

    db.commit()

    sel = db.query(Selection).filter(Selection.user_id == user.id).first()
    prof = db.query(Professor).filter(Professor.id == sel.professor_id).first()

    return MySelectionRes(
        student_no=user.student_no,
        name=user.name,
        professor_id=sel.professor_id,
        professor_name=(prof.name if prof else None),
        method=sel.method,
    )

@app.get("/admin/dashboard", response_model=AdminDashboardRes)
def admin_dashboard(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    win = get_window(db)
    professors = db.query(Professor).order_by(Professor.id.asc()).all()

    student_counts = dict(
        db.query(Selection.professor_id, func.count(Selection.id))
          .filter(Selection.method == "student")
          .group_by(Selection.professor_id)
          .all()
    )
    total_counts = dict(
        db.query(Selection.professor_id, func.count(Selection.id))
          .group_by(Selection.professor_id)
          .all()
    )

    prof_items = []
    for p in professors:
        sc = int(student_counts.get(p.id, 0))
        tc = int(total_counts.get(p.id, 0))
        prof_items.append(AdminDashboardItem(
            professor_id=p.id,
            professor_name=p.name,
            student_count=sc,
            base_capacity=p.base_capacity,
            extra_capacity=p.extra_capacity,
            total_count=tc,
            total_capacity=p.base_capacity + p.extra_capacity
        ))

    subq = db.query(Selection.user_id).subquery()
    unassigned_users = db.query(User).filter(~User.id.in_(select(subq.c.user_id))).all()
    unassigned = [MySelectionRes(student_no=u.student_no, name=u.name) for u in unassigned_users]

    return AdminDashboardRes(
        window=window_response(win),
        professors=prof_items,
        unassigned_students=unassigned
    )

@app.post("/admin/add-seat")
def admin_add_seat(payload: AdminAddSeatReq, db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    with db.begin():
        p = db.execute(select(Professor).where(Professor.id == payload.professor_id).with_for_update()).scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="교수를 찾을 수 없습니다")
        p.extra_capacity += int(payload.count)

    return {"ok": True, "professor_id": payload.professor_id, "extra_capacity": p.extra_capacity}

@app.post("/admin/assign")
def admin_assign(payload: AdminAssignReq, db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    # 입장 안 한 학생도 배정 가능: allowed_students에서 확인 후 users 자동 생성
    user = db.query(User).filter(User.student_no == payload.student_no).first()
    if not user:
        allowed = db.query(AllowedStudent).filter(AllowedStudent.student_no == payload.student_no).first()
        if not allowed:
            raise HTTPException(status_code=404, detail="사전등록(allowed_students)에 없는 학번입니다")
        user = User(student_no=allowed.student_no, name=allowed.name)
        db.add(user)
        db.commit()
        db.refresh(user)

    with db.begin():
        p = db.execute(select(Professor).where(Professor.id == payload.professor_id).with_for_update()).scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="교수를 찾을 수 없습니다")

        total_capacity = p.base_capacity + p.extra_capacity
        total_count = int(db.query(func.count(Selection.id)).filter(Selection.professor_id == p.id).scalar() or 0)
        if total_count >= total_capacity:
            raise HTTPException(status_code=409, detail="최종 정원이 부족합니다. 좌석을 추가하세요(/admin/add-seat).")

        sel = db.query(Selection).filter(Selection.user_id == user.id).first()
        if not sel:
            db.add(Selection(user_id=user.id, professor_id=p.id, method="admin"))
        else:
            sel.professor_id = p.id
            sel.method = "admin"

    return {"ok": True, "student_no": payload.student_no, "professor_id": payload.professor_id}

@app.post("/admin/assign-random")
def admin_assign_random(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    # 1) 교수 목록 + 현재 배정 수/정원 계산
    professors = db.query(Professor).filter(Professor.active == True).order_by(Professor.id.asc()).all()
    if not professors:
        raise HTTPException(status_code=400, detail="활성 교수 목록이 없습니다")

    total_counts = dict(
        db.query(Selection.professor_id, func.count(Selection.id))
          .group_by(Selection.professor_id)
          .all()
    )

    remaining = {}
    for p in professors:
        total_capacity = int(p.base_capacity + p.extra_capacity)
        used = int(total_counts.get(p.id, 0))
        remaining[p.id] = max(0, total_capacity - used)

    # 배정 가능한 좌석이 하나도 없으면 종료
    if sum(remaining.values()) <= 0:
        return {"ok": True, "assigned": 0, "skipped": 0, "detail": "배정 가능한 좌석이 없습니다."}

    # 2) 미배정 학생(allowed_students 기준, 선택 없는 학생) 목록 만들기
    # AllowedStudent -> User(없을 수도) -> Selection(없어야 미배정)
    rows = (
        db.query(AllowedStudent.student_no, AllowedStudent.name, User.id.label("user_id"))
        .outerjoin(User, User.student_no == AllowedStudent.student_no)
        .outerjoin(Selection, Selection.user_id == User.id)
        .filter(Selection.id == None)   # Selection이 없으면 미배정
        .all()
    )

    if not rows:
        return {"ok": True, "assigned": 0, "skipped": 0, "detail": "미배정 학생이 없습니다."}

    # 랜덤성을 위해 학생 순서 섞기
    rows = list(rows)
    random.shuffle(rows)

    assigned = 0
    skipped = 0

    # 3) 한 명씩 랜덤 교수 배정 (남은 좌석이 있는 교수 중 랜덤)
    for student_no, name, user_id in rows:
        # 좌석이 남은 교수들만 후보
        candidates = [pid for pid, rem in remaining.items() if rem > 0]
        if not candidates:
            skipped += 1
            continue

        professor_id = random.choice(candidates)

        # user가 없으면 생성
        if not user_id:
            user = User(student_no=student_no, name=name)
            db.add(user)
            db.flush()  # user.id 확보
            user_id = user.id

        # selection이 없다는 조건으로 뽑았지만, 안전하게 다시 체크
        sel = db.query(Selection).filter(Selection.user_id == user_id).first()
        if sel:
            skipped += 1
            continue

        db.add(Selection(user_id=user_id, professor_id=professor_id, method="random"))
        remaining[professor_id] -= 1
        assigned += 1

    db.commit()

    return {"ok": True, "assigned": assigned, "skipped": skipped}

@app.post("/admin/reset-random")
def admin_reset_random(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    # method가 random인 배정만 삭제
    deleted = (
        db.query(Selection)
        .filter(Selection.method == "random")
        .delete()
    )

    db.commit()
    return {"ok": True, "deleted": int(deleted)}

@app.get("/admin/roster")
def admin_roster(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    rows = (
        db.query(
            AllowedStudent.student_no,
            AllowedStudent.name,
            Professor.name.label("professor_name"),
            Selection.method.label("method"),
        )
        .outerjoin(User, User.student_no == AllowedStudent.student_no)
        .outerjoin(Selection, Selection.user_id == User.id)
        .outerjoin(Professor, Professor.id == Selection.professor_id)
        .order_by(AllowedStudent.student_no.asc())
        .all()
    )

    result = []
    for student_no, name, professor_name, method in rows:
        result.append({
            "student_no": student_no,
            "name": name,
            "professor_name": professor_name,
            "method": method,
            "status": ("assigned" if professor_name else "unassigned"),
        })
    return {"count": len(result), "items": result}

@app.get("/admin/export.csv")
def admin_export_csv(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    if not require_admin_key(x_admin_key):
        raise HTTPException(status_code=401, detail="admin key invalid")

    rows = (
        db.query(
            AllowedStudent.student_no,
            AllowedStudent.name,
            Professor.name.label("professor_name"),
            Selection.method.label("method"),
        )
        .outerjoin(User, User.student_no == AllowedStudent.student_no)
        .outerjoin(Selection, Selection.user_id == User.id)
        .outerjoin(Professor, Professor.id == Selection.professor_id)
        .order_by(AllowedStudent.student_no.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_no", "name", "professor_name", "method", "status"])
    for student_no, name, professor_name, method in rows:
        status = "assigned" if professor_name else "unassigned"
        writer.writerow([student_no, name, professor_name or "", method or "", status])

    data = output.getvalue()
    output.close()

    bom = "\ufeff"
    csv_bytes = (bom + data).encode("utf-8")

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=advisor_allocation_2026-1.csv"},
    )