from flask import Flask, request
import datetime
import re
import pickle
import sys
from googleapiclient.discovery import build
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai
import os

import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)


# === Gig parser ===
def parse_with_gpt(body):
    try:
        system_prompt = """
You are a helpful assistant that extracts gig, session, or reminder details from unstructured Hebrew messages and returns structured JSON.

Your job is to interpret casual, often messy messages and output clear structured data.

### Output Format:
Always respond with only valid JSON in this structure:

{
  "type": "gig" | "session" | "reminder",
  "date": "DD.MM.YYYY",
  "time": "HH:MM",
  "location": "string",
  "description": "string",
  "show_length": "string (e.g. '45 דקות מופע' or '4 שעות')",
  "sound_and_lighting": "string",
  "confirmation": "string",
  "title": "string",
  "datetime_string": "string (e.g. 'מחר ב-10' or 'ביום שני ב-18:00')" // only for reminders
}

### Rules:

- Classify type based on content:
  - If the message is a **performance** or **rehearsal**, set `"type": "gig"`
  - If the message describes a **סשן** (session), including סשן בוקר or סשן ערב, set `"type": "session"`
  - If the message is a personal reminder or task (e.g. 'תזכור', 'אל תשכח', 'לסדר', 'לקנות', 'להתקשר') — set `"type": "reminder"`

- For reminders, only fill:
  - type = "reminder"
  - description = short text of the task
  - datetime_string = if any vague or exact time is mentioned (e.g. 'מחר ב-10', 'ביום ראשון ב-18:00'), translate it into natural English for the Todoist API (e.g. "tomorrow at 10am", "Sunday at 6pm")
  - All other fields should be empty strings

- For gigs or sessions:
  - Never guess missing data. If a field is not mentioned, leave it as an empty string.
  - Do not invent or change the date. Extract it exactly as written (e.g. '16.5.25').
  - If a time range is mentioned (e.g. 11:00-15:00), use the start time as "time" and calculate the duration as "show_length" (e.g. "4 שעות").
  - If the message includes:
      - 'סשן עם <name>'
      - 'סשן בוקר עם <name>'
      - 'סשן ערב עם <name>'
    Then:
      - Set `"type": "session"`
      - Use the full phrase before "עם" as the event type (e.g. "סשן ערב")
      - Append the name after "עם"
      - Format title as: '<event type> <name>'

  - If message contains phrases like:
      - 'חזרה עם <name>'
      - 'הופעה עם <name>'
    Then:
      - Set `"type": "gig"`
      - Same title logic applies

  - If title includes:
    - 'סשן בוקר' with no time/show_length → set:
      - "time": "11:00"
      - "show_length": "4 שעות"
    - 'סשן ערב' with no time/show_length → set:
      - "time": "15:00"
      - "show_length": "4 שעות"

  - If no clear title is found, use default:
    - For gigs: "הופעה סטטיק"
    - For sessions: "סשן"

- Do not include any explanation or notes — only return the JSON.
        """

        messages = [{
            "role": "system",
            "content": system_prompt.strip()
        }, {
            "role": "user",
            "content": body.strip()
        }]

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                messages=messages)

        raw_text = response["choices"][0]["message"]["content"]
        print("🧠 GPT raw:", raw_text)
        parsed = eval(
            raw_text)  # quick + dirty for now — we'll tighten it later
        return parsed

    except Exception as e:
        print("❌ GPT parse failed:", e)
        return {
            'date': '',
            'location': '',
            'time': '',
            'description': '',
            'show_length': '',
            'sound_and_lighting': '',
            'confirmation': '',
            'title': 'הופעה סטטיק'
        }


def parse_gig_message(body):
    data = {
        'date': '',
        'location': '',
        'time': '',
        'description': '',
        'show_length': '',
        'sound_and_lighting': '',
        'confirmation': '',
        'title': 'הופעה סטטיק'
    }

    lines = body.strip().split('\n')
    found_date = False
    location_assigned = False

    for line in lines:
        line = line.strip()

        if not data['date']:
            match = re.match(r'\d{1,2}\.\d{1,2}\.\d{2,4}', line)
            if match:
                data['date'] = match.group()
                found_date = True
                continue

        if found_date and not location_assigned:
            if (not re.search(r'\d{1,2}:\d{2}', line)
                    and not line.startswith('שעת עלייה')
                    and not any(keyword in line for keyword in [
                        'מופע', 'דקות', 'הגברה', 'תאורה', 'נא לאשר', 'אירוע',
                        'בר מצווה', 'חתונה'
                    ]) and len(line.split()) > 1  # avoid one-word junk
                ):
                data['location'] = line
                location_assigned = True
                continue

        if line.startswith('שעת עלייה'):
            match = re.search(r'\d{1,2}:\d{2}', line)
            if match:
                data['time'] = match.group()
                continue

        if 'מופע' in line or 'דקות' in line:
            data['show_length'] = line.strip()
            continue

        if 'הגברה' in line or 'תאורה' in line:
            data['sound_and_lighting'] = line.strip()
            continue

        if 'נא לאשר' in line:
            data['confirmation'] = line.strip()
            continue

        if not data['description'] and data['location']:
            data['description'] = line

    return data


# === Calendar event creator ===
def create_calendar_event(parsed):
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

        service = build('calendar', 'v3', credentials=creds)

        date_parts = parsed['date'].split('.')

        # Handle both dd.mm.yy and dd.mm.yyyy
        day, month, year = date_parts
        if len(year) == 2:
            year = '20' + year  # convert 25 → 2025

        date_str = f"{year}-{month}-{day}"
        datetime_start = datetime.datetime.strptime(
            f"{date_str} {parsed['time']}", "%Y-%m-%d %H:%M")

        if 'שעתיים' in parsed['show_length']:
            duration_hours = 2
        elif '45' in parsed['show_length']:
            duration_hours = 0.75
        else:
            duration_hours = 1

        datetime_end = datetime_start + datetime.timedelta(
            hours=duration_hours)

        event = {
            'summary': parsed['title'],
            'location': parsed['location'],
            'description':
            f"{parsed['description']}\n{parsed['sound_and_lighting']}\n{parsed['confirmation']}",
            'start': {
                'dateTime': datetime_start.isoformat(),
                'timeZone': 'Asia/Jerusalem',
            },
            'end': {
                'dateTime': datetime_end.isoformat(),
                'timeZone': 'Asia/Jerusalem',
            },
        }

        result = service.events().insert(calendarId='primary',
                                         body=event).execute()
        print("✅ Event created:", result.get('htmlLink'))
        sys.stdout.flush()

    except Exception as e:
        print("❌ Calendar error:", e)
        sys.stdout.flush()


def log_to_google_sheets(parsed):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open("Gig Log").sheet1  # Assumes first sheet
        row = [
            parsed['date'],
            parsed['time'],
            parsed['location'],
            parsed['description'],
            parsed['show_length'],
            parsed['sound_and_lighting'],
            parsed['confirmation'],
        ]
        sheet.append_row(row)
        print("🟢 Gig logged to Google Sheets.")
        sys.stdout.flush()
    except Exception as e:
        print("❌ Google Sheets error:", e)
        sys.stdout.flush()


        # === Webhook ===
@app.route("/", methods=["POST"])
def handle_whatsapp():
    try:
        body = (request.form.get("Body")
                or (request.get_json(silent=True) or {}).get("Body")
                or request.data.decode())

        print("📩 Raw message:", repr(body))
        parsed = parse_with_gpt(body)

        if parsed["type"] == "reminder":
            from todoist_utils import add_todoist_task
            task_text = parsed.get("description", "משימה ללא שם")
            due = parsed.get("datetime_string") or None
            result = add_todoist_task(task_text, due_string=due)
            print("✅ Task sent to Todoist:", result)

        # Existing logic like:
        # create_calendar_event(parsed)
        # log_to_google_sheets(parsed)

        return "OK", 200
    except Exception as e:
        print("❌ ERROR:", str(e))
        sys.stdout.flush()
        return "ERROR", 500


if __name__ == "__main__":
    print("🔥 Flask app is running")
    sys.stdout.flush()
    app.run(host="0.0.0.0", port=3000)
