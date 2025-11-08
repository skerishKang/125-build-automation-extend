"""자연어 날짜/시간 파싱 유틸리티."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


def parse_relative_date_time(
    text: str,
    reference: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """한국어 자연어 표현에서 날짜/시간과 지속 시간을 추출한다."""

    reference = reference or datetime.now().astimezone()
    date = None
    time_hour: Optional[int] = None
    time_minute = 0
    duration_minutes = 60

    lowered = text.lower()

    if "모레" in lowered:
        date = (reference + timedelta(days=2)).date()
    elif "내일모레" in lowered or "글피" in lowered:
        date = (reference + timedelta(days=3)).date()
    elif "내일" in lowered:
        date = (reference + timedelta(days=1)).date()
    elif "오늘" in lowered:
        date = reference.date()

    month_day_match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if month_day_match:
        month = int(month_day_match.group(1))
        day = int(month_day_match.group(2))
        year = reference.year
        if month < reference.month or (month == reference.month and day < reference.day):
            year += 1
        date = datetime(year, month, day).date()

    date_match_alt = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if date_match_alt and not month_day_match:
        month = int(date_match_alt.group(1))
        day = int(date_match_alt.group(2))
        year = reference.year
        if month < reference.month or (month == reference.month and day < reference.day):
            year += 1
        date = datetime(year, month, day).date()

    if date is None:
        date = reference.date()

    meridiem_offset = 0
    if any(token in lowered for token in ["오후", "저녁", "밤", "pm"]):
        meridiem_offset = 12
    if any(token in lowered for token in ["오전", "아침", "새벽", "am"]):
        meridiem_offset = 0

    time_match = re.search(r"(\d{1,2})\s*시\s*(\d{1,2})?\s*분?", text)
    if time_match:
        time_hour = int(time_match.group(1))
        minutes = time_match.group(2)
        time_minute = int(minutes) if minutes else 0
    else:
        colon_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if colon_match:
            time_hour = int(colon_match.group(1))
            time_minute = int(colon_match.group(2))

    if time_hour is None:
        time_hour = 9

    if meridiem_offset == 12 and time_hour < 12:
        time_hour += 12
    if meridiem_offset == 0 and time_hour == 12 and "오전" in lowered:
        time_hour = 0

    duration_match_hours = re.search(r"(\d{1,2})\s*시간", text)
    duration_match_minutes = re.search(r"(\d{1,3})\s*(분|min|minute|minutes)", lowered)

    if duration_match_minutes:
        try:
            duration_minutes = max(10, min(int(duration_match_minutes.group(1)), 720))
        except ValueError:
            duration_minutes = 60
    elif duration_match_hours:
        try:
            duration_minutes = max(30, min(int(duration_match_hours.group(1)) * 60, 720))
        except ValueError:
            duration_minutes = 60

    start_dt = datetime.combine(date, datetime.min.time()).replace(
        hour=time_hour,
        minute=time_minute,
        tzinfo=reference.tzinfo,
    )

    if meridiem_offset == 0 and time_hour < 12:
        if reference.hour >= time_hour and start_dt.date() == reference.date():
            start_dt = start_dt + timedelta(hours=12)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    return {
        "start": start_dt,
        "end": end_dt,
        "duration_minutes": duration_minutes,
    }
