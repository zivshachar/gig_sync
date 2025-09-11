
import requests
import os

# === Load all Todoist projects once ===
def get_todoist_projects():
    token = os.environ["TODOIST_API_TOKEN"]
    response = requests.get(
        "https://api.todoist.com/rest/v2/projects",
        headers={"Authorization": f"Bearer {token}"}
    )
    return {p["name"]: p["id"] for p in response.json()}

# Save the project list when the server starts
todoist_projects = get_todoist_projects()

def resolve_project_id(project_name):
    return todoist_projects.get(project_name)

def add_todoist_task(content, due_string=None, project_id=None):
    token = os.environ.get("TODOIST_API_TOKEN")

    url = 'https://api.todoist.com/rest/v2/tasks'
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "content": content,
    }

    if due_string:
        data["due_string"] = due_string
    if project_id:
        data["project_id"] = project_id

    response = requests.post(url, json=data, headers=headers)
    return response.json() if response.ok else {"error": response.text}
