"""
Google Calendar Service - Monitor and Manage Google Calendar Events
"""
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from google.oauth2 import service_account

logger = logging.getLogger("calendar_service")

# Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']
_calendar_service = None

DEFAULT_SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    '..',
    'service_account.json',
)

SERVICE_ACCOUNT_FILE = os.getenv('CALENDAR_SERVICE_ACCOUNT_FILE') or DEFAULT_SERVICE_ACCOUNT_FILE
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID') or 'padiemipu@gmail.com'




def get_calendar_service():
    """Get or create Google Calendar service object."""
    global _calendar_service

    if _calendar_service is None:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=SCOPES,
            )
            _calendar_service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar service initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize Google Calendar service: %s", exc)
            raise

    return _calendar_service


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_events_in_range(start_time: datetime, end_time: datetime, max_results: int = 50) -> List[Dict[str, Any]]:
    """Get events in a specific time range."""
    service = get_calendar_service()

    try:
        start_time = _ensure_tz(start_time)
        end_time = _ensure_tz(end_time)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
        ).execute()

        events = events_result.get('items', [])
        logger.info("Found %d events in range", len(events))
        return events

    except Exception as exc:
        logger.error("Error getting events: %s", exc)
        return []


def get_today_events() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return get_events_in_range(today_start, today_end)


def get_tomorrow_events() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    tomorrow_end = tomorrow_start + timedelta(days=1)
    return get_events_in_range(tomorrow_start, tomorrow_end)


def get_week_events() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    return get_events_in_range(week_start, week_end, max_results=100)


def get_upcoming_events(minutes_ahead: int = 30) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=minutes_ahead)

    try:
        service = get_calendar_service()

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime',
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
        ).execute()

        events = events_result.get('items', [])
        logger.info("Found %d upcoming events", len(events))
        return events

    except Exception as exc:
        logger.error("Error getting upcoming events: %s", exc)
        return []


def search_events(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    service = get_calendar_service()

    try:
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(days=365)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=future_time.isoformat(),
            q=query,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
        ).execute()

        events = events_result.get('items', [])
        logger.info("Found %d events matching '%s'", len(events), query)
        return events

    except Exception as exc:
        logger.error("Error searching events: %s", exc)
        return []


def format_event_datetime(start: Dict[str, str], end: Dict[str, str]) -> str:
    start_time = start.get('dateTime', start.get('date'))
    end_time = end.get('dateTime', end.get('date'))

    if not start_time:
        return "시간 정보 없음"

    if 'T' not in start_time:
        return "종일"

    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else start_dt
        return f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    except Exception as exc:
        logger.error("Error parsing datetime: %s", exc)
        return "시간 정보 없음"


def format_event_list(events: List[Dict[str, Any]], title: str = "일정") -> str:
    if not events:
        return f"📅 {title}이(가) 없습니다."

    lines = [f"📅 **{title}** ({len(events)}개)\n"]

    for i, event in enumerate(events, 1):
        start = event.get('start', {})
        end = event.get('end', {})
        time_str = format_event_datetime(start, end)
        event_title = event.get('summary', '제목 없음')

        line = f"{i}. **{event_title}**\n"
        line += f"   ⏰ {time_str}\n"

        if event.get('location'):
            line += f"   📍 {event['location']}\n"

        if event.get('description'):
            desc = event['description'][:100]
            if len(event['description']) > 100:
                desc += "..."
            line += f"   📝 {desc}\n"

        if event.get('htmlLink'):
            line += f"   🔗 {event['htmlLink']}\n"

        lines.append(line)

    return "\n".join(lines)


def create_event(summary: str, start_dt: datetime, end_dt: datetime, description: str = "", location: str = "") -> Dict[str, Any]:
    service = get_calendar_service()

    start_dt = _ensure_tz(start_dt)
    end_dt = _ensure_tz(end_dt)

    event_body: Dict[str, Any] = {
        'summary': summary,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'Asia/Seoul',
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'Asia/Seoul',
        },
    }

    if description:
        event_body['description'] = description
    if location:
        event_body['location'] = location

    logger.info("Attempting to create event with calendarId: %s and body: %s", CALENDAR_ID, event_body)

    created_event = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event_body,
    ).execute()

    logger.info("Created calendar event: %s", created_event.get('id'))
    return created_event
