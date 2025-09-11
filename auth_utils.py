import os
import json
from google.oauth2.service_account import Credentials

# Scopes for all Google services used
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive"
]

def load_google_credentials():
    """
    Loads Google service account credentials from GOOGLE_SERVICE_ACCOUNT_JSON env var.
    """
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise EnvironmentError("Missing GOOGLE_SERVICE_ACCOUNT_JSON")
    creds_info = json.loads(creds_json)
    return Credentials.from_service_account_info(creds_info, scopes=GOOGLE_SCOPES)

def get_twilio_credentials():
    """
    Returns Twilio account SID and Auth Token from env.
    """
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise EnvironmentError("Missing Twilio credentials")
    return sid, token

def get_openai_api_key():
    """
    Returns OpenAI API key from env.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("Missing OPENAI_API_KEY")
    return key

def get_todoist_api_key():
    """
    Returns Todoist API key from env.
    """
    token = os.getenv("TODOIST_API_KEY")
    if not token:
        raise EnvironmentError("Missing TODOIST_API_KEY")
    return token
