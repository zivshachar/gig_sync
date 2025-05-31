
def generate_response(parsed):
    try:
        t = parsed.get("type", "unknown")

        if t == "reminder":
            time = parsed.get("datetime_string", "")
            task = parsed.get("description", "")
            return f"📝 נוספה תזכורת: '{task}' ל-{time}"

        elif t == "project_setup":
            name = parsed.get("project_name", "")
            count = len(parsed.get("tasks", []))
            return f"📋 יצרת פרויקט חדש בשם '{name}' עם {count} משימות"

        elif t == "query":
            intent = parsed.get("intent", "")
            day = parsed.get("target_day", "")
            keyword = parsed.get("search_keywords", "")

            if intent == "day_summary":
                return f"בודק מה יש לך ביום {day}..."
            elif intent == "week_summary":
                return f"📅 בודק את כל השבוע הקרוב..."
            elif intent == "has_event":
                return f"בודק אם יש לך {keyword} ביום {day}..."
            elif intent == "next_event":
                return "🔎 מחפש את האירוע הקרוב ביותר שלך..."
            else:
                return "🔍 מבצע בדיקה בלו״ז שלך..."

        elif t == "calendar_event":
            title = parsed.get("description", "")
            time = parsed.get("datetime_string", "")
            return f"📆 נוסף אירוע בלו״ז: {title} בשעה {time}"

        elif t == "drive_action":
            return "📂 מבצע פעולה על הקבצים בדרייב שלך..."

        elif t == "unknown":
            return "❓ לא הבנתי את הבקשה, נסה לנסח אחרת."

        else:
            return "🤖 הבקשה שלך טופלה."

    except Exception as e:
        print("❌ chat_reply error:", e)
        return "❌ קרתה שגיאה בהבנת הבקשה שלך."
