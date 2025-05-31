from datetime import datetime, timedelta
import pytz


def execute_action(parsed, calendar_service):
    tz = pytz.timezone("Asia/Jerusalem")
    from calendar_utils import get_events_on_day, get_next_event

    action = parsed.get("action", "")
    date_str = parsed.get("date", "")
    template = parsed.get("reply_template", "")
    keyword = parsed.get("keywords", "").lower()
    query_type = parsed.get("query_type", "")

    if date_str:
        try:
            day = tz.localize(datetime.strptime(date_str, "%Y-%m-%d"))
        except Exception:
            return "❌ לא הצלחתי להבין את התאריך שביקשת"
    else:
        day = tz.localize(datetime.now())

    if action == "lookup_calendar":
        if query_type == "first_event":
            events = get_events_on_day(calendar_service, "primary",
                                       day.strftime("%Y-%m-%d"))
            if events:
                first = events[0]
                title = first["summary"]
                time = first["start"]["dateTime"][11:16]
                return template.format(time=time, title=title)
            else:
                return "אין לך כלום באותו יום 📭"

        elif query_type == "next_event":
            e = get_next_event(calendar_service, "primary")[0]
            title = e["summary"]
            date = e["start"]["dateTime"][:10]
            time = e["start"]["dateTime"][11:16]
            return f"האירוע הבא שלך הוא {title} בתאריך {date} בשעה {time}"

        elif query_type == "full_day":
            events = get_events_on_day(calendar_service, "primary",
                                       day.strftime("%Y-%m-%d"))
            if not events:
                return "אין לך כלום ביום הזה 📭"
            lines = [
                f"🗓 {e['summary']} בשעה {e['start'].get('dateTime', '')[11:16]}"
                for e in events
            ]
            return "\n".join(lines)

        elif query_type == "has_event":
            events = get_events_on_day(calendar_service, "primary",
                                       day.strftime("%Y-%m-%d"))
            if keyword:
                found = any(keyword in e["summary"].lower() for e in events)
                return f"✅ כן, יש לך {keyword}" if found else f"❌ אין {keyword} ביום הזה"
            else:
                return f"יש {len(events)} אירועים ביום הזה." if events else "אין אירועים באותו יום."

        else:
            return "🔍 מחפש בלו״ז שלך..."

    elif action == "add_calendar_event":
        try:
            print("📦 Creating event with:")
            print("Summary:", parsed.get("title"))
            print("Start time:", parsed.get("start_time"))
            print("Location:", parsed.get("location"))
            print("Description:", parsed.get("description"))
            print("Duration:", parsed.get("duration"))

            start_str = parsed.get(
                "start_time")  # expected: "2025-05-20T22:30:00"
            start_dt = tz.localize(
                datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S"))
            end_dt = start_dt + timedelta(minutes=parsed.get("duration", 60))

            event = {
                'summary': parsed.get("title", "אירוע ללא שם"),
                'location': parsed.get("location", ""),
                'description': parsed.get("description", ""),
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Jerusalem',
                },
            }

            calendar_service.events().insert(calendarId='primary',
                                             body=event).execute()
            result = calendar_service.events().insert(calendarId='primary',
                                                      body=event).execute()
            print("📆 Google Calendar result:", result)
            return f"✅ האירוע '{event['summary']}' נוסף ליומן שלך"

        except Exception as e:
            print("❌ Calendar error:", e)
            return f"❌ שגיאה בהוספת אירוע: {str(e)}"

    elif action == "add_task":
        from todoist_utils import add_todoist_task
        task_text = parsed.get("keywords") or parsed.get(
            "description") or "משימה ללא שם"
        due = parsed.get("date", None)
        project_id = None  # can be added later if needed
        print("📝 Adding Todoist task:", task_text, "| Due:", due)
        result = add_todoist_task(task_text,
                                  due_string=due,
                                  project_id=project_id)
        print("📤 Todoist API result:", result)
        return parsed.get("reply_template") or "📝 המשימה נוספה"

    elif action == "reply_naturally":
        return template or "🤖 זה מה שאני יודע: ..."

    return "🤷 לא הצלחתי להבין מה לעשות עם הבקשה שלך."
