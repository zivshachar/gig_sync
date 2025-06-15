import os
import json
import logging
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import openai
from datetime import datetime
import traceback

from todoist_utils import (get_todoist_projects, create_todoist_project,
                           archive_project, add_todoist_task,
                           add_tasks_to_project, list_tasks_due_today,
                           complete_task, delete_task, resolve_project_id)
from sheets_utils import (build_sheets_client, open_sheet, append_row,
                          log_event, fetch_income_summary, get_gig_history)
from calendar_utils import (build_calendar_service, add_calendar_event,
                            get_events_on_day, check_calendar_conflict,
                            get_next_event, scan_week_schedule)
from drive_utils import (build_drive_service, upload_file, list_drive_files,
                         delete_file, download_file, export_google_doc)
from auth_utils import (load_google_credentials, get_twilio_credentials,
                        get_openai_api_key, get_todoist_api_key)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials
creds = load_google_credentials()
twilio_sid, twilio_token = get_twilio_credentials()
openai.api_key = get_openai_api_key()
todoist_token = get_todoist_api_key()


class WhatsAppAssistant:

    def __init__(self):
        self.available_functions = {
            # Todoist
            'get_todoist_projects': get_todoist_projects,
            'create_todoist_project': create_todoist_project,
            'archive_project': archive_project,
            'add_todoist_task': add_todoist_task,
            'add_tasks_to_project': add_tasks_to_project,
            'list_tasks_due_today': list_tasks_due_today,
            'complete_task': complete_task,
            'delete_task': delete_task,
            'resolve_project_id': resolve_project_id,

            # Calendar
            'build_calendar_service': build_calendar_service,
            'add_calendar_event': add_calendar_event,
            'get_events_on_day': get_events_on_day,
            'check_calendar_conflict': check_calendar_conflict,
            'get_next_event': get_next_event,
            'scan_week_schedule': scan_week_schedule,

            # Sheets
            'build_sheets_client': build_sheets_client,
            'open_sheet': open_sheet,
            'append_row': append_row,
            'log_event': log_event,
            'fetch_income_summary': fetch_income_summary,
            'get_gig_history': get_gig_history,

            # Drive
            'build_drive_service': build_drive_service,
            'upload_file': upload_file,
            'list_drive_files': list_drive_files,
            'delete_file': delete_file,
            'download_file': download_file,
            'export_google_doc': export_google_doc,
        }

    def process_message(self, user_message):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "You are a helpful WhatsApp assistant."
                }, {
                    "role": "user",
                    "content": user_message
                }],
                functions=[{
                    "name": name
                } for name in self.available_functions],
                function_call="auto")

            message = response.choices[0].message
            if message.get("function_call"):
                function_name = message["function_call"]["name"]
                arguments = json.loads(message["function_call"]["arguments"])
                logger.info(
                    f"Calling function: {function_name} with args: {json.dumps(arguments, indent=2)}"
                )

                if function_name.startswith("build_"):
                    result = self.available_functions[function_name](creds)
                else:
                    result = self.available_functions[function_name](
                        **arguments)

                return str(result)
            else:
                return message.get("content", "No response.")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())
            return "Sorry, I encountered an error processing your request."


assistant = WhatsAppAssistant()


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        logger.info(f"Received message from {from_number}: {incoming_msg}")
        if not incoming_msg:
            return str(MessagingResponse())

        response_text = assistant.process_message(incoming_msg)

        resp = MessagingResponse()
        resp.message(response_text)
        logger.info(f"Sending response: {response_text}")
        return str(resp)

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        logger.error(traceback.format_exc())
        resp = MessagingResponse()
        resp.message("Sorry, I'm experiencing technical difficulties.")
        return str(resp)


@app.route('/', methods=['GET'])
def home():
    return f"""
    <html><head><title>WhatsApp Assistant</title></head>
    <body style='font-family:sans-serif;'>
    <h1>✅ Assistant is Running</h1>
    <p>Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>Use the /test endpoint to debug, or send WhatsApp messages via Twilio webhook.</p>
    </body></html>
    """


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/test', methods=['POST'])
def test_message():
    try:
        data = request.get_json()
        message = data.get('message', '')
        if not message:
            return jsonify({"error": "No message provided"}), 400
        response = assistant.process_message(message)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
