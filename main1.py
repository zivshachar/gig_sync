import os
import json
import logging
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import openai
from datetime import datetime, timedelta
import traceback

# Import your utility modules
try:
    from todoist_utils import (
        get_todoist_projects, create_todoist_project, archive_project,
        add_todoist_task, add_tasks_to_project, list_tasks_due_today,
        complete_task, delete_task, resolve_project_id
    )
    from sheets_utils import (
        build_sheets_client, open_sheet, append_row, log_event,
        fetch_income_summary, get_gig_history
    )
    from calendar_utils import (
        build_calendar_service, add_calendar_event, get_events_on_day,
        check_calendar_conflict, get_next_event, scan_week_schedule
    )
    from drive_utils import (
        build_drive_service, upload_file, list_drive_files,
        delete_file, download_file, export_google_doc
    )
except ImportError as e:
    logging.error(f"Failed to import utility modules: {e}")

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

class WhatsAppAssistant:
    def __init__(self):
        self.available_functions = {
            # Todoist functions
            'get_todoist_projects': get_todoist_projects,
            'create_todoist_project': create_todoist_project,
            'archive_project': archive_project,
            'add_todoist_task': add_todoist_task,
            'add_tasks_to_project': add_tasks_to_project,
            'list_tasks_due_today': list_tasks_due_today,
            'complete_task': complete_task,
            'delete_task': delete_task,
            'resolve_project_id': resolve_project_id,

            # Sheets functions
            'build_sheets_client': build_sheets_client,
            'open_sheet': open_sheet,
            'append_row': append_row,
            'log_event': log_event,
            'fetch_income_summary': fetch_income_summary,
            'get_gig_history': get_gig_history,

            # Calendar functions
            'build_calendar_service': build_calendar_service,
            'add_calendar_event': add_calendar_event,
            'get_events_on_day': get_events_on_day,
            'check_calendar_conflict': check_calendar_conflict,
            'get_next_event': get_next_event,
            'scan_week_schedule': scan_week_schedule,

            # Drive functions
            'build_drive_service': build_drive_service,
            'upload_file': upload_file,
            'list_drive_files': list_drive_files,
            'delete_file': delete_file,
            'download_file': download_file,
            'export_google_doc': export_google_doc
        }

        self.function_descriptions = [
            {
                "name": "get_todoist_projects",
                "description": "Get all Todoist projects",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "add_todoist_task",
                "description": "Add a task to Todoist",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_text": {"type": "string", "description": "Task content/description"},
                        "due_string": {"type": "string", "description": "Due date as string (optional)"},
                        "project_id": {"type": "string", "description": "Project ID (optional)"}
                    },
                    "required": ["task_text"]
                }
            },
            {
                "name": "list_tasks_due_today",
                "description": "List all tasks due today",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "complete_task",
                "description": "Mark a task as complete",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "get_events_on_day",
                "description": "Get calendar events for a specific day",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "calendar_service": {"type": "string", "description": "Calendar service (will be built automatically)"},
                        "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
                    },
                    "required": ["date"]
                }
            },
            {
                "name": "get_next_event",
                "description": "Get the next upcoming calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "calendar_service": {"type": "string", "description": "Calendar service (will be built automatically)"},
                        "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"}
                    },
                    "required": []
                }
            },
            {
                "name": "scan_week_schedule",
                "description": "Get schedule for the current week",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "fetch_income_summary",
                "description": "Get income summary from Google Sheets",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "get_gig_history",
                "description": "Get gig work history from Google Sheets",
                "parameters": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "list_drive_files",
                "description": "List files in Google Drive",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        ]

    def get_gpt_response_with_functions(self, user_message):
        """Get GPT response and determine if function calling is needed"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful WhatsApp assistant that can manage tasks, calendar events, and documents. 
                        You have access to various functions for Todoist, Google Calendar, Google Sheets, and Google Drive.

                        When users ask you to:
                        - Add tasks, create projects, or manage todos → use Todoist functions
                        - Schedule events, check calendar, or manage appointments → use Calendar functions  
                        - Track income, log events, or manage data → use Sheets functions
                        - Manage files or documents → use Drive functions

                        Always try to be helpful and execute the requested actions. If you need to call a function, do so.
                        Keep responses concise and friendly for WhatsApp."""
                    },
                    {"role": "user", "content": user_message}
                ],
                functions=self.function_descriptions,
                function_call="auto"
            )

            return response
        except Exception as e:
            logger.error(f"Error getting GPT response: {e}")
            return None

    def execute_function(self, function_name, arguments):
        """Execute the specified function with given arguments"""
        try:
            if function_name not in self.available_functions:
                return f"Function {function_name} not available"

            func = self.available_functions[function_name]

            # Convert arguments if they're a string
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            # Handle calendar functions that need service
            if function_name in ['get_events_on_day', 'get_next_event']:
                try:
                    # Try to build calendar service - your function might handle credentials differently
                    calendar_service = build_calendar_service()
                    if function_name == 'get_events_on_day':
                        date = arguments.get('date')
                        calendar_id = arguments.get('calendar_id', 'primary')
                        result = func(calendar_service, calendar_id, date)
                    elif function_name == 'get_next_event':
                        calendar_id = arguments.get('calendar_id', 'primary')  
                        result = func(calendar_service, calendar_id)
                    return result
                except Exception as calendar_error:
                    logger.error(f"Calendar service error: {calendar_error}")
                    return f"❌ Calendar service not available: {str(calendar_error)}"

            # Handle sheets functions that might need service
            if function_name in ['fetch_income_summary', 'get_gig_history', 'log_event', 'append_row']:
                try:
                    # These might need sheets service
                    result = func(**arguments) if arguments else func()
                    return result
                except Exception as sheets_error:
                    logger.error(f"Sheets service error: {sheets_error}")
                    return f"❌ Sheets service not available: {str(sheets_error)}"

            # Handle drive functions
            if function_name in ['list_drive_files', 'upload_file', 'download_file', 'delete_file', 'export_google_doc']:
                try:
                    result = func(**arguments) if arguments else func()
                    return result
                except Exception as drive_error:
                    logger.error(f"Drive service error: {drive_error}")
                    return f"❌ Drive service not available: {str(drive_error)}"

            # Get function signature to debug parameter issues
            import inspect
            sig = inspect.signature(func)
            logger.info(f"Function {function_name} expects parameters: {list(sig.parameters.keys())}")
            logger.info(f"Trying to call with: {arguments}")

            # Call the function with unpacked arguments
            result = func(**arguments) if arguments else func()
            return result

        except TypeError as te:
            logger.error(f"Parameter mismatch for {function_name}: {te}")
            # Try calling without arguments if parameter mismatch
            try:
                result = self.available_functions[function_name]()
                return f"Called {function_name} without parameters (parameter mismatch): {result}"
            except:
                return f"Function {function_name} parameter error: {str(te)}"
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"

    def process_message(self, user_message):
        """Process incoming WhatsApp message and return response"""
        try:
            # Try to log the incoming message (optional, don't fail if it doesn't work)
            try:
                log_event("whatsapp_message", {"message": user_message, "timestamp": datetime.now().isoformat()})
            except Exception as log_error:
                logger.warning(f"Failed to log event: {log_error}")

            # Get GPT response
            gpt_response = self.get_gpt_response_with_functions(user_message)

            if not gpt_response:
                return "Sorry, I'm having trouble processing your request right now."

            message = gpt_response.choices[0].message

            # Check if GPT wants to call a function
            if message.get("function_call"):
                function_name = message["function_call"]["name"]
                function_args = message["function_call"]["arguments"]

                logger.info(f"Calling function: {function_name} with args: {function_args}")

                # Execute the function
                function_result = self.execute_function(function_name, function_args)

                # Get GPT's final response with function result
                final_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful WhatsApp assistant. Provide a concise, friendly response based on the function result."
                        },
                        {"role": "user", "content": user_message},
                        message,
                        {
                            "role": "function",
                            "name": function_name,
                            "content": str(function_result)
                        }
                    ]
                )

                return final_response.choices[0].message.content

            else:
                # Return GPT's direct response
                return message.content

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())
            return "Sorry, I encountered an error processing your request. Please try again."

# Initialize the assistant
assistant = WhatsAppAssistant()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages via Twilio webhook"""
    try:
        # Get the incoming message
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')

        logger.info(f"Received message from {from_number}: {incoming_msg}")

        if not incoming_msg:
            return str(MessagingResponse())

        # Process the message with the assistant
        response_text = assistant.process_message(incoming_msg)

        # Create Twilio response
        resp = MessagingResponse()
        resp.message(response_text)

        logger.info(f"Sending response: {response_text}")

        return str(resp)

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        logger.error(traceback.format_exc())

        resp = MessagingResponse()
        resp.message("Sorry, I'm experiencing technical difficulties. Please try again later.")
        return str(resp)

@app.route('/', methods=['GET'])
def home():
    """Home page with simple web interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #25D366; text-align: center; }
            .status { padding: 15px; background: #e8f5e8; border-radius: 5px; margin: 20px 0; }
            .test-form { background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }
            input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #25D366; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #1ea952; }
            .response { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #25D366; }
            .functions { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .function-list { columns: 2; column-gap: 20px; }
            .function-item { break-inside: avoid; margin: 5px 0; padding: 5px; background: white; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 WhatsApp Assistant Dashboard</h1>

            <div class="status">
                <strong>✅ Status:</strong> Assistant is running and ready!<br>
                <strong>🕐 Started:</strong> ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''<br>
                <strong>📱 Webhook:</strong> /webhook (for Twilio)<br>
                <strong>🔗 Test API:</strong> /test (POST)
            </div>

            <div class="test-form">
                <h3>🧪 Test the Assistant</h3>
                <textarea id="testMessage" placeholder="Type a message to test the assistant... 
Examples:
- Add a task to buy groceries
- What's on my calendar today?
- Show me my projects
- Schedule a meeting tomorrow at 2pm" rows="4"></textarea>
                <button onclick="testAssistant()">Send Test Message</button>
                <div id="response"></div>
            </div>

            <div class="functions">
                <h3>🛠️ Available Functions</h3>
                <div class="function-list">
                    <div class="function-item"><strong>📋 Todoist:</strong> Tasks, projects, due dates</div>
                    <div class="function-item"><strong>📅 Calendar:</strong> Events, scheduling, conflicts</div>
                    <div class="function-item"><strong>📊 Sheets:</strong> Income tracking, gig history</div>
                    <div class="function-item"><strong>📁 Drive:</strong> File management, documents</div>
                </div>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #666;">
                <p>Send messages via WhatsApp or use the test form above</p>
            </div>
        </div>

        <script>
            async function testAssistant() {
                const message = document.getElementById('testMessage').value;
                const responseDiv = document.getElementById('response');

                if (!message.trim()) {
                    alert('Please enter a message to test');
                    return;
                }

                responseDiv.innerHTML = '<div style="padding: 10px; background: #fff3cd; border-radius: 5px;">🤔 Processing...</div>';

                try {
                    const response = await fetch('/test', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        responseDiv.innerHTML = '<div class="response"><strong>🤖 Assistant Response:</strong><br>' + data.response + '</div>';
                    } else {
                        responseDiv.innerHTML = '<div style="padding: 10px; background: #f8d7da; border-radius: 5px; color: #721c24;"><strong>❌ Error:</strong> ' + data.error + '</div>';
                    }
                } catch (error) {
                    responseDiv.innerHTML = '<div style="padding: 10px; background: #f8d7da; border-radius: 5px; color: #721c24;"><strong>❌ Error:</strong> ' + error.message + '</div>';
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/test', methods=['POST'])
def test_message():
    """Test endpoint for debugging"""
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
    # Verify required environment variables
    required_env_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)

    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)