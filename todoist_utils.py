
import requests
import os

TOKEN = os.environ.get("TODOIST_API_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# === Project-related ===

def get_todoist_projects():
    res = requests.get("https://api.todoist.com/rest/v2/projects", headers=HEADERS)
    return res.json() if res.ok else []

def create_todoist_project(name):
    data = {"name": name}
    res = requests.post("https://api.todoist.com/rest/v2/projects", headers=HEADERS, json=data)
    return res.json() if res.ok else {"error": res.text}

def archive_project(project_id):
    url = f"https://api.todoist.com/rest/v2/projects/{project_id}"
    res = requests.delete(url, headers=HEADERS)
    return res.status_code == 204

# === Task-related ===

def add_todoist_task(content, due_string=None, project_id=None):
    data = {"content": content}
    if due_string:
        data["due_string"] = due_string
    if project_id:
        data["project_id"] = project_id
    res = requests.post("https://api.todoist.com/rest/v2/tasks", headers=HEADERS, json=data)
    return res.json() if res.ok else {"error": res.text}

def add_tasks_to_project(task_list, project_id):
    results = []
    for task in task_list:
        results.append(add_todoist_task(task, project_id=project_id))
    return results

def list_tasks_due_today(project_id=None):
    res = requests.get("https://api.todoist.com/rest/v2/tasks", headers=HEADERS)
    if not res.ok:
        return []
    from datetime import datetime
    today = datetime.now().date().isoformat()
    tasks = res.json()
    return [t for t in tasks if t.get("due", {}).get("date") == today and (not project_id or t["project_id"] == project_id)]

def complete_task(task_name):
    tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers=HEADERS).json()
    for task in tasks:
        if task_name in task["content"]:
            task_id = task["id"]
            res = requests.post(f"https://api.todoist.com/rest/v2/tasks/{task_id}/close", headers=HEADERS)
            return res.status_code == 204
    return False

def delete_task(task_name):
    tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers=HEADERS).json()
    for task in tasks:
        if task_name in task["content"]:
            task_id = task["id"]
            res = requests.delete(f"https://api.todoist.com/rest/v2/tasks/{task_id}", headers=HEADERS)
            return res.status_code == 204
    return False

def resolve_project_id(project_name):
    projects = get_todoist_projects()
    match = next((p for p in projects if project_name.strip() in p["name"]), None)
    return match["id"] if match else None
