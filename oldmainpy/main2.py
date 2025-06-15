from flask import Flask, request
import os
import openai
import json
import pytz
from datetime import datetime, timedelta
from parser import parse_message_with_gpt
from chat_reply import generate_response
from action_handler import execute_action
from calendar_utils import (build_calendar_service, get_events_on_day, 
                            check_calendar_conflict, get_next_event,
                            add_calendar_event, 


def resolve_natural_date(day_keyword):
    today = dt.datetime.now(pytz.timezone("Asia/Jerusalem")).date()
    weekday_map = {
        "ראשון": 6, "שני": 0, "שלישי": 1, "רביעי": 2,
        "חמישי": 3, "שישי": 4, "שבת": 5,
        "sunday": 6, "monday": 0, "tuesday": 1,
        "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5
    }

    for word, target_day in weekday_map.items():
        if word in day_keyword.lower():
            today_weekday = today.weekday()
            days_ahead = (target_day - today_weekday + 7) % 7
            if days_ahead == 0:
                days_ahead = 7  # jump to next week if same day
            return (today + dt.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # fallback if no match
    return day_keyword  # assume GPT returned a valid YYYY-MM-DD


scan_week_schedule)


# === Import utility modules ===
from todoist_utils import (add_todoist_task, add_tasks_to_project,
                           complete_task, create_todoist_project, delete_task,
                           list_tasks_due_today, resolve_project_id)

from sheets_utils import (build_sheets_client, open_sheet, log_event)
from drive_utils import (build_drive_service, upload_file, list_drive_files,
                         download_file, export_google_doc)

from twilio.rest import Client

calendar_id = os.environ.get("CALENDAR_ID")  # must be your personal Gmail


app = Flask(__name__)

# === SETUP ===
openai.api_key = os.environ["OPENAI_API_KEY"]
calendar_credentials = None
sheet_client = None
sheet = None


def init_google_services():
    global calendar_credentials, sheet_client, sheet
    import json
    from oauth2client.service_account import ServiceAccountCredentials

    scopes = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    creds_dict = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
    calendar_credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict, scopes)

    sheet_client = build_sheets_client()
    sheet = open_sheet(sheet_client, os.environ.get("SHEET_NAME", "Gig Log"))


init_google_services()
calendar_service = build_calendar_service(calendar_credentials)


def send_whatsapp_reply(to_number, message):
    client = Client(os.environ["TWILIO_ACCOUNT_SID"],
                    os.environ["TWILIO_AUTH_TOKEN"])
    from_number = "whatsapp:+14155238886"  # ← hardcoded Twilio sandbox number
    to_number = "whatsapp:" + to_number.replace("whatsapp:",
                                                "")  # ← ensures correct format

    client.messages.create(body=message, from_=from_number, to=to_number)


@app.route("/", methods=["POST"])
def handle_whatsapp():
    try:
        body = request.form.get("Body")
        sender = request.form.get("From")
        print("📩 Incoming message:", body)

        parsed = parse_message_with_gpt(body)
        print("🧠 GPT raw:", parsed)

        reply = execute_action(parsed, calendar_service)
        send_whatsapp_reply(sender, reply)

        return "OK", 200

    except Exception as e:
        print("❌ Error:", e)
        send_whatsapp_reply(sender, "קרתה שגיאה פנימית. נסה שוב.")
        return "error", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
