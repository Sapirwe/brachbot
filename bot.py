import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tokens
import re

# Initialize OpenAI API with your GPT-3.5 API key
openai.api_key = tokens.API_gpt_token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום! שלח לי שם של מאכל או מנה ואני אחזיר לך את הברכה המתאימה. אני יכול לטפל במנות מורכבות כמו 'סלט קינואה עם חזה עוף' או מאכלים פשוטים")

async def get_bracha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    food_name = update.message.text.strip()
    
    # Smart prompt that lets GPT do all the thinking
    prompt = f"""
    אתה מומחה בהלכה יהודית. המשתמש שואל על הברכה הנכונה לפני אכילת: "{food_name}"

    כללי הברכות (בסדר חשיבות):
    
    **חשוב מאוד - ברכה ראשונה:**
    - "המוציא לחם מן הארץ" - לכל סוגי הלחם והמאפים (לחם, פיתות, לחמניה, בייגל, מצה, פיתה, לאפה וכו')
    
    **אם זה לא לחם, השתמש באחת מהברכות הבאות:**
    - "בורא פרי העץ" - לפירות עצים (תפוח, תפוז, בננה וכו')
    - "בורא פרי האדמה" - לירקות מהאדמה (גזר, תפוח אדמה, עגבניה וכו')
    - "שהכל נהיה בדברו" - למזונות מעובדים (בשר, דגים, ביצים, אומלט, חביתה וכו')
    - "בורא מיני מזונות" - למוצרי דגן שאינם לחם (אורז, פסטה, קינואה, קרואסון, עוגה, עוגיות וכו')

    עבור מנות מורכבות, זהה את המרכיב העיקרי והשתמש בברכה המתאימה.

    אם "{food_name}" הוא לא מאכל (כמו בעלי חיים, חפצים, אנשים וכו') - תשיב: "{food_name} זה לא מאכל"

    תשובה בעברית בלבד:
    """

    try:
        # Let GPT do all the work
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1  # Very low temperature for consistent responses
        )
        
        # Get GPT's response
        gpt_response = response['choices'][0]['message']['content'].strip()
        
        # Check if GPT says it's not a food
        if "זה לא מאכל" in gpt_response:
            await update.message.reply_text(gpt_response)
            return
        
        # Extract just the blessing from GPT response
        blessing_patterns = [
            r'המוציא לחם מן הארץ',
            r'בורא פרי העץ',
            r'בורא פרי האדמה', 
            r'שהכל נהיה בדברו',
            r'בורא מיני מזונות'
        ]
        
        final_blessing = None
        for pattern in blessing_patterns:
            match = re.search(pattern, gpt_response)
            if match:
                final_blessing = match.group(0)
                break
        
        # If GPT didn't give a valid blessing, use default
        if final_blessing is None:
            final_blessing = "שהכל נהיה בדברו"
        
        # Send ONLY the blessing
        await update.message.reply_text(final_blessing)
        
    except Exception as e:
        # Simple fallback if API fails
        await update.message.reply_text("שהכל נהיה בדברו")

def main():
    # Initialize the Telegram bot
    app = ApplicationBuilder().token(tokens.telegram_bot_token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bracha))
    
    # Run the bot
    app.run_polling()

if __name__ == "__main__":
    main()
