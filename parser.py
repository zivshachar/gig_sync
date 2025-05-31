import openai
import json
from datetime import datetime, timedelta


def load_system_prompt():
    with open("gpt_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()


from datetime import datetime, timedelta
import pytz


    from datetime import datetime, timedelta
    import pytz

    def resolve_date(text):
        tz = pytz.timezone("Asia/Jerusalem")
        today = datetime.now(tz).date()
        text = text.strip().lower()

        if "next week" in text:
            days_until_sunday = (6 - today.weekday() + 1) % 7
            return (today + timedelta(days=days_until_sunday)).strftime("%Y-%m-%d")

        if "מחר" in text or "tomorrow" in text:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")

        if "היום" in text or "today" in text:
            return today.strftime("%Y-%m-%d")

        # Weekday map
        weekday_map = {
            "ראשון": 6, "sunday": 6,
            "שני": 0, "monday": 0,
            "שלישי": 1, "tuesday": 1,
            "רביעי": 2, "wednesday": 2,
            "חמישי": 3, "thursday": 3,
            "שישי": 4, "friday": 4,
            "שבת": 5, "saturday": 5
        }

        for word, target_day in weekday_map.items():
            if word in text:
                current_day = today.weekday()
                days_ahead = (target_day - current_day + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # If already in YYYY-MM-DD format, return as-is
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            return today.strftime("%Y-%m-%d")  # fallback = today
            


def parse_message_with_gpt(text, model="gpt-4"):
    prompt = load_system_prompt()
    messages = [{
        "role": "system",
        "content": prompt
    }, {
        "role": "user",
        "content": text
    }]
    try:
        response = openai.ChatCompletion.create(model=model, messages=messages)
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, list):
            parsed = parsed[0]

        if "target_day" in parsed:
            parsed["target_day"] = resolve_date(parsed["target_day"])

        return parsed
    except Exception as e:
        print("❌ GPT parsing error:", e)
        return {"type": "unknown", "raw": text}
