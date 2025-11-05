from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta, timezone

# Setup credentials
credentials = service_account.Credentials.from_service_account_file(
    'service_account.json',
    scopes=['https://www.googleapis.com/auth/calendar.readonly']
)
service = build('calendar', 'v3', credentials=credentials)

try:
    # Test 1: Get calendar list
    calendars = service.calendarList().list().execute()
    print(f"Success! Found {len(calendars['items'])} calendars")

    # Test 2: Get events from primary calendar
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat(),
        timeMax=tomorrow.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    print(f"Found {len(events)} events for tomorrow")

except Exception as e:
    print(f"Failed: {e}")
