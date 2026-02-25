from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
TITLE = "2026년 1학기 바이오캡스톤디자인(생명공학과)"

# ✅ DB에는 UTC를 "naive datetime"으로 저장/비교 (tzinfo 없음)
def now_utc() -> datetime:
    return datetime.utcnow()  # naive UTC

def utc_to_kst_str(dt_utc: datetime) -> str:
    """
    dt_utc: naive UTC로 가정
    """
    aware_utc = dt_utc.replace(tzinfo=timezone.utc)
    return aware_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M")

def kst_str_to_utc(dt_str: str) -> datetime:
    """
    "YYYY-MM-DD HH:MM" (KST) -> naive UTC datetime
    """
    local = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    utc_aware = local.astimezone(timezone.utc)
    return utc_aware.replace(tzinfo=None)  # ✅ naive UTC로 저장

def is_window_open(now: datetime, start_at: datetime, end_at: datetime, enabled: bool) -> bool:
    if not enabled:
        return False
    # ✅ now/start/end 모두 naive UTC라는 전제
    return start_at <= now <= end_at