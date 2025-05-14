import os
import requests

def add_todoist_task(content, due_string=None, project_id=None):
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        raise Exception("Missing TODOIST_API_TOKEN in environment variables")

    url = 'https://api.todoist.com/rest/v2/tasks'
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"content": content}
    if due_string:
        data["due_string"] = due_string
    if project_id:
        data["project_id"] = project_id

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200 or response.status_code == 204:
        return {"success": True}
    else:
        return {"success": False, "error": response.text}