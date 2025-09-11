
import gspread
from datetime import datetime
import os
import requests

HEADERS = {
    "Authorization": f"Bearer {os.getenv('TODOIST_API_KEY')}",
    "Content-Type": "application/json"
}

def add_todoist_task(content, due_string=None, project_id=None):
    data = {"content": content}
    if due_string:
        data["due_string"] = due_string
    if project_id:
        data["project_id"] = project_id
    res = requests.post("https://api.todoist.com/rest/v2/tasks", headers=HEADERS, json=data)
    print("📤 Todoist response:", res.status_code, res.text)
    return res.json() if res.ok else {"error": res.text}

def build_sheets_client():
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    import json
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    return gc

def open_sheet(gc, sheet_name):
    return gc.open(sheet_name).sheet1

def append_row(sheet, row):
    sheet.append_row(row)

def log_event(sheet, parsed):
    row = [
        parsed.get("date", ""),
        parsed.get("time", ""),
        parsed.get("title", ""),
        parsed.get("location", ""),
        parsed.get("show_length", ""),
        parsed.get("sound_and_lighting", ""),
        parsed.get("description", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    sheet.append_row(row)

def fetch_income_summary(sheet, col=8):
    records = sheet.col_values(col)
    income = 0
    for r in records[1:]:
        try:
            income += float(r)
        except:
            continue
    return income

def get_gig_history(sheet, limit=10):
    data = sheet.get_all_values()
    headers = data[0]
    rows = data[-limit:]
    return [dict(zip(headers, row)) for row in rows]
