from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz


def build_calendar_service(credentials):
    return build("calendar", "v3", credentials=credentials)


def add_calendar_event(service, summary, location, start_dt, duration_minutes):
    import os
    from datetime import timedelta

    calendar_id = os.environ.get("CALENDAR_ID")
    print("📅 add_calendar_event using calendar_id:", calendar_id)

    end_dt = start_dt + timedelta(minutes=duration_minutes)
    event = {
        "summary": summary,
        "location": location,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Jerusalem"
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Jerusalem"
        }
    }
    return service.events().insert(calendarId=calendar_id,
                                   body=event).execute()


def get_events_on_day(service, calendar_id, date_str):
    tz = pytz.timezone("Asia/Jerusalem")
    start = tz.localize(datetime.strptime(date_str, "%Y-%m-%d"))
    end = start + timedelta(days=1)
    result = service.events().list(calendarId=calendar_id,
                                   timeMin=start.isoformat(),
                                   timeMax=end.isoformat(),
                                   singleEvents=True,
                                   orderBy='startTime').execute()
    return result.get("items", [])


def check_calendar_conflict(service, calendar_id, start_dt, duration_minutes):
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    result = service.events().list(calendarId=calendar_id,
                                   timeMin=start_dt.isoformat(),
                                   timeMax=end_dt.isoformat(),
                                   singleEvents=True,
                                   orderBy='startTime').execute()
    return result.get("items", [])


def get_next_event(service, calendar_id):
    now = datetime.now(pytz.timezone("Asia/Jerusalem")).isoformat()
    result = service.events().list(calendarId=calendar_id,
                                   timeMin=now,
                                   maxResults=1,
                                   singleEvents=True,
                                   orderBy='startTime').execute()
    return result.get("items", [])


def scan_week_schedule(service, calendar_id):
    tz = pytz.timezone("Asia/Jerusalem")
    start = tz.localize(datetime.now())
    end = start + timedelta(days=7)
    result = service.events().list(calendarId=calendar_id,
                                   timeMin=start.isoformat(),
                                   timeMax=end.isoformat(),
                                   singleEvents=True,
                                   orderBy='startTime').execute()
    return result.get("items", [])
