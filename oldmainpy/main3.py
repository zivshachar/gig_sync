from flask import Flask, request
import os
import openai
import json
from datetime import datetime, timedelta
import pytz
from parser import parse_message_with_gpt
from chat_reply import generate_response
from action_handler import execute_action
from calendar_utils import (
    build_calendar_service, add_calendar_event, get_events_on_day, get_next_event, scan_week_schedule,)

# === Twilio ===
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# === Google Auth ===
from google.oauth2 import service_account

app = Flask(__name__)

# === Load secrets ===
openai.api_key = os.environ["OPENAI_API_KEY"]
calendar_id = os.environ.get("CALENDAR_ID")

# === Build Google service ===
calendar_credentials = service_account.Credentials.from_service_account_file(
    "service-account.json",  # make sure this file is in your Replit
    scopes=["https://www.googleapis.com/auth/calendar"])
calendar_service = build_calendar_service(calendar_credentials)

def resolve_natural_date(raw_date):
    tz = pytz.timezone("Asia/Jerusalem")
    today = datetime.now(tz).date()

    # if already a valid date string, return as-is
    try:
        datetime.strptime(raw_date, "%Y-%m-%d")
        return raw_date
    except ValueError:
        pass

    # weekday mapping
    weekday_map = {
        "ראשון": 6,
        "שני": 0,
        "שלישי": 1,
        "רביעי": 2,
        "חמישי": 3,
        "שישי": 4,
        "שבת": 5,
        "sunday": 6,
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5
    }

    for word, target_day in weekday_map.items():
        if word in raw_date.lower():
            today_weekday = today.weekday()
            delta = (target_day - today_weekday + 7) % 7
            if delta == 0:
                delta = 7  # go to next week if it's today
            resolved_date = today + timedelta(days=delta)
            return resolved_date.strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")  # fallback = today


@app.route("/", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    print(f"📩 Incoming message: {incoming_msg}")

    try:
        parsed = parse_message_with_gpt(incoming_msg)
        print("🧠 GPT raw:", parsed)

        if parsed["action"] == "add_calendar_event":
            start_time = datetime.fromisoformat(parsed["start_time"])
            result = add_calendar_event(calendar_service,
                                        summary=parsed["title"],
                                        location=parsed["location"],
                                        start_dt=start_time,
                                        duration_minutes=parsed["duration"])
            print("📆 Google Calendar result:", result)
            reply_text = parsed["reply_template"]

        elif parsed["action"] == "lookup_calendar":
            # Resolve natural date language like "שלישי"
            date_str = resolve_date(parsed["date"])
            print("🧪 Final resolved date:", date_str)
            
            # 🔐 Make sure calendar_id and service are correct
            print("🧪 DEBUG: calendar_id =", calendar_id)
            print("🧪 DEBUG: calendar_service =", type(calendar_service))

            events = get_events_on_day(calendar_service, calendar_id, date_str)

            if not events:
                reply_text = "אין לך שום אירועים ביום הזה 🎉"
            else:
                first_event = events[0]
                title = first_event.get("summary", "אירוע ללא שם")

                try:
                    time = datetime.fromisoformat(
                        first_event["start"]["dateTime"]).strftime("%H:%M")
                except KeyError:
                    time = "שעה לא ידועה"

                reply_text = parsed["reply_template"].format(title=title,
                                                             time=time)

        else:
            reply_text = generate_response(parsed)

    except Exception as e:
        print("❌ ERROR:", str(e))
        reply_text = "מצטער, הייתה שגיאה בטיפול בבקשה שלך."

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
