
import json
import re
import asyncio

# --- OpenAI (modern client) ---
try:
    from openai import OpenAI
    _USING_RESPONSES_API = True
except Exception:
    # Fallback to legacy interface if needed
    import openai  # type: ignore
    _USING_RESPONSES_API = False

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import tokens  # expects: tokens.API_gpt_token, tokens.telegram_bot_token


# =====================
# Config
# =====================
MODEL = "gpt-4o-mini"  # fast + inexpensive; upgrade as you wish

# JSON Schema for Structured Outputs
BRACHABOT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_food": {"type": "boolean"},
        "category": {
            "type": "string",
            "enum": ["לחם", "מזונות", "פרי_עץ", "פרי_אדמה", "יין", "שהכל", "לא_מאכל", "לא_ידוע"],
        },
        "bracha": {
            "type": "string",
            "description": "הברכה הראשונה המתאימה או '—' אם לא מאכל/לא ידוע",
        },
        "explanation": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["is_food", "category", "bracha", "explanation"],
    "additionalProperties": False,
}

# Deterministic mapping (server-side safety)
CATEGORY_TO_BRACHA = {
    "לחם": "המוציא לחם מן הארץ",
    "מזונות": "בורא מיני מזונות",
    "פרי_עץ": "בורא פרי העץ",
    "פרי_אדמה": "בורא פרי האדמה",
    "יין": "בורא פרי הגפן",
    "שהכל": "שהכל נהיה בדברו",
}


SYSTEM_PROMPT = """
אתה מומחה בהלכה יהודית בענייני ברכות. מטרתך: לקבוע ברכה ראשונה מדויקת לפי כללים הלכתיים נפוצים.
אם הקלט אינו מאכל – עליך לציין זאת במפורש. החזר JSON תקין בלבד לפי הסכימה שסופקה.

כללים תמציתיים:
- לחם ודומיו (פת): "המוציא".
- דגנים שאינם לחם (פת הבאה בכסנין, עוגות/עוגיות/בורקס, דייסות, קוסקוס/פסטה/איטריות/בורגול/אורז מבושלים): "מזונות".
- פרי עץ אמיתי: "בורא פרי העץ".
- גידולי קרקע שאינם עץ (לרבות בננה): "בורא פרי האדמה".
- יין (יין אדום, יין לבן, יין מתוק, מיץ ענבים לקידוש): "יין".
- בשר/דגים/ביצים/גבינות/משקאות/ממתקים/מאכלים מעובדים/תערובות ללא רכיב דגן עיקרי: "שהכל".
- מנה מורכבת: המרכיב העיקרי קובע.
- אם זה לא מאכל: is_food=false, category="לא_מאכל", bracha="—".
- אם חסר מידע או קיימת מחלוקת משמעותית: category="לא_ידוע" עם הסבר קצר.

דוגמאות קצרות (לא תיאור מלא):
- "תפוח" → פרי_עץ/בורא פרי העץ.
- "בננה" → פרי_אדמה/בורא פרי האדמה.
- "קרואסון" (רגיל, לא קביעת סעודה) → מזונות/בורא מיני מזונות.
- "שניצל" → שהכל/שהכל נהיה בדברו.

החזר אך ורק JSON — ללא טקסט נוסף.
""".strip()


# =====================
# OpenAI helpers
# =====================
def _coerce_bracha(category: str, bracha_from_model: str) -> str:
    """Prefer deterministic mapping; return '—' for non-food/unknown."""
    category = (category or "").strip()
    bracha_from_model = (bracha_from_model or "").strip()
    if category in ("לא_מאכל", "לא_ידוע"):
        return "—"
    mapped = CATEGORY_TO_BRACHA.get(category)
    if mapped:
        return mapped
    # Last resort: model's suggestion or default
    return bracha_from_model or "שהכל נהיה בדברו"


def _legacy_chat_completion(food_name: str, details: str = "") -> dict:
    """Legacy fallback using ChatCompletion with JSON instruction."""
    import openai  # legacy
    openai.api_key = tokens.API_gpt_token
    user_prompt = f'שם המאכל: "{food_name}"\\nתיאור (אופציונלי): {details or "—"}'
    json_only = (
        "החזר JSON תקין בלבד לפי הסכימה: "
        + json.dumps(BRACHABOT_SCHEMA, ensure_ascii=False)
    )

    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\\n\\n" + json_only},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    text = resp["choices"][0]["message"]["content"]
    return json.loads(text)


def ask_openai(food_name: str, details: str = "") -> dict:
    """
    Calls OpenAI with Structured Outputs if available; else uses legacy fallback.
    Returns a dict that matches BRACHABOT_SCHEMA.
    """
    if not _USING_RESPONSES_API:
        return _legacy_chat_completion(food_name, details)

    client = OpenAI(api_key=tokens.API_gpt_token)
    user_prompt = f'שם המאכל: "{food_name}"\\nתיאור (אופציונלי): {details or "—"}'

    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "brachabot", "schema": BRACHABOT_SCHEMA},
        },
    )
    # Try to extract the JSON payload robustly
    try:
        text = resp.output[0].content[0].text  # standard path
    except Exception:
        # Fallback: some SDKs expose .output_text or similar
        text = getattr(resp, "output_text", None) or getattr(resp, "content", None)
        if text is None:
            # Last resort: convert to str and try to find JSON in it
            raw = str(resp)
            m = re.search(r"\\{.*\\}", raw, flags=re.S)
            text = m.group(0) if m else "{}"

    return json.loads(text)


# =====================
# Telegram Handlers
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "שלום! שלח/י שם של מאכל או מנה (גם מורכבת) ואחזיר את הברכה המתאימה.\n"
        "דוגמה: 'סלט קינואה עם חזה עוף', 'תפוח', 'קרואסון'."
    )


async def get_bracha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    food_name = (update.message.text or "").strip()
    if not food_name:
        await update.message.reply_text("שלח/י שם מאכל אחד 😄")
        return

    try:
        data = ask_openai(food_name)
        is_food = bool(data.get("is_food"))
        category = str(data.get("category", "לא_ידוע"))
        bracha_model = str(data.get("bracha", ""))
        final_bracha = _coerce_bracha(category, bracha_model)

        if not is_food or category == "לא_מאכל" or final_bracha == "—":
            await update.message.reply_text(f"{food_name} זה לא מאכל")
            return

        # Send ONLY the blessing text (as you requested)
        await update.message.reply_text(final_bracha)

    except Exception as e:
        # Fallback if something goes wrong
        await update.message.reply_text("שהכל נהיה בדברו")


def main():
    app = ApplicationBuilder().token(tokens.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bracha))
    app.run_polling()


if __name__ == "__main__":
    main()
