"""
Google Calendar Service - Monitor and Read Google Calendar Events
"""
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account

logger = logging.getLogger("calendar_service")

# Service account key file path
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'service_account.json')

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Cache the service object
_calendar_service = None


def get_calendar_service():
    """Get or create Google Calendar service object"""
    global _calendar_service

    if _calendar_service is None:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
            _calendar_service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            raise

    return _calendar_service


def get_events_in_range(start_time: datetime, end_time: datetime, max_results: int = 50) -> List[Dict[str, Any]]:
    """Get events in a specific time range"""
    service = get_calendar_service()

    try:
        # Use timezone-aware datetime
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} events in range")
        return events

    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return []


def get_today_events() -> List[Dict[str, Any]]:
    """Get today's events"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    return get_events_in_range(today_start, today_end)


def get_tomorrow_events() -> List[Dict[str, Any]]:
    """Get tomorrow's events"""
    now = datetime.now(timezone.utc)
    tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    return get_events_in_range(tomorrow_start, tomorrow_end)


def get_week_events() -> List[Dict[str, Any]]:
    """Get this week's events (Monday to Sunday)"""
    now = datetime.now(timezone.utc)
    # Get start of current week (Monday)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    return get_events_in_range(week_start, week_end, max_results=100)


def get_upcoming_events(minutes_ahead: int = 30) -> List[Dict[str, Any]]:
    """Get events starting within the next X minutes"""
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=minutes_ahead)

    try:
        service = get_calendar_service()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} upcoming events")
        return events

    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        return []


def search_events(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Search for events by keyword"""
    service = get_calendar_service()

    try:
        # Search in future events
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(days=365)  # Search in next year

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=future_time.isoformat(),
            q=query,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} events matching '{query}'")
        return events

    except Exception as e:
        logger.error(f"Error searching events: {e}")
        return []


def format_event_datetime(start: Dict[str, str], end: Dict[str, str]) -> str:
    """Format event start and end time for display"""
    start_time = start.get('dateTime', start.get('date'))
    end_time = end.get('dateTime', end.get('date'))

    # Check if it's an all-day event
    if 'T' not in start_time:
        return "종일"

    # Parse datetime strings
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

        # Format time range
        time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
        return time_str
    except Exception as e:
        logger.error(f"Error parsing datetime: {e}")
        return "시간 정보 없음"


def format_event_list(events: List[Dict[str, Any]], title: str = "일정") -> str:
    """Format event list for Telegram message"""
    if not events:
        return f"📅 {title}이(가) 없습니다."

    lines = [f"📅 **{title}** ({len(events)}개)\n"]

    for i, event in enumerate(events, 1):
        start = event.get('start', {})
        end = event.get('end', {})
        time_str = format_event_datetime(start, end)

        # Event title
        title = event.get('summary', '제목 없음')

        # Build line
        line = f"{i}. **{title}**\n"
        line += f"   ⏰ {time_str}\n"

        # Add location if available
        if event.get('location'):
            line += f"   📍 {event['location']}\n"

        # Add description preview if available
        if event.get('description'):
            desc = event['description'][:100]
            if len(event.get('description', '')) > 100:
                desc += "..."
            line += f"   📝 {desc}\n"

        # Add link if available
        if event.get('htmlLink'):
            line += f"   🔗 {event['htmlLink']}\n"

        lines.append(line)

    return "\n".join(lines)


def get_today_summary() -> str:
    """Get a summary of today's events"""
    events = get_today_events()

    if not events:
        return """
📅 **오늘의 일정** 🎉

등록된 일정이 없습니다.
멋진 하루 보내세요!
        """.strip()

    # Count events
    total_events = len(events)

    # Find first and last event
    first_event = events[0]
    last_event = events[-1]

    # Format summary
    summary = f"""
📅 **오늘의 일정** ({total_events}개)

🗓️ {first_event['start'].get('dateTime', first_event['start'].get('date', ''))[:10]}
    """.strip()

    # Add event list
    for i, event in enumerate(events, 1):
        start = event.get('start', {})
        time_str = format_event_datetime(start, event.get('end', {}))
        title = event.get('summary', '제목 없음')

        # Add emoji for important events
        emoji = "⭐" if event.get('description') and ('important' in event['description'].lower() or '긴급' in event['description']) else "•"

        summary += f"\n{emoji} {i}. {time_str} - {title}"

    # Add footer
    summary += f"""

💡 **다른 명령어**:
• `/cal_tomorrow` - 내일 일정
• `/cal_week` - 이번 주 전체 일정
• `/cal_search <키워드>` - 일정 검색
    """.strip()

    return summary
