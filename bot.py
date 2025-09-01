import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tokens

# Initialize OpenAI API with your GPT-3.5 API key
openai.api_key = tokens.API_gpt_token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום, שלח לי שם של מאכל ואני אחזיר לך את הברכה שלו")



async def get_bracha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    food_name = update.message.text

    # prompt = f"""
    # Hello GPT,
    # You are an expert in Jewish blessings for foods. Please provide an accurate response according to Jewish Halacha (Orthodox tradition). 
    # Your response must include only the blessing and must follow this format: 
    # על {food_name} מברכים - "הברכה המתאימה".

    # For example, if the food is an apple, your answer should look like this:
    # על תפוח מברכים - "בורא פרי העץ".

    # If the answer depends on additional variables, provide a more detailed explanation.
    # If the food is not a type of food you usually eat, return: {food_name} זה לא מאכל.

    # The question is: What is the correct blessing for "{food_name}"?
    # Please provide your answer in Hebrew only.
    # """

    prompt = f"""
    You are a Jewish Rabbi expert in Halacha (Jewish law). 

    The user is asking for the correct blessing (bracha) before eating "{food_name}".

    IMPORTANT RULES:
    - Only return the blessing text, nothing else
    - Use ONLY these 4 standard blessings:
    * "בורא פרי העץ" - for tree fruits (apples, oranges, etc.)
    * "בורא פרי האדמה" - for ground vegetables (carrots, potatoes, etc.)
    * "שהכל נהיה בדברו" - for processed foods (bread, cookies, etc.)
    * "בורא מיני מזונות" - for grain products (rice, pasta, etc.)

    - If "{food_name}" is NOT a food item, return: "{food_name} זה לא מאכל"
    - If you're unsure, return: "שהכל נהיה בדברו" (the general blessing)

    Question: What blessing for "{food_name}"?
    Answer in Hebrew only:
"""


    # Query GPT-3.5 API to determine the blessing for the given food
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    
    # Extract the response text from GPT-3.5's answer
    blessing = response['choices'][0]['message']['content'].strip()

    await update.message.reply_text(blessing)

def main():
    # Initialize the Telegram bot
    app = ApplicationBuilder().token(tokens.telegram_bot_token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_bracha))
    
    # Run the bot
    app.run_polling()

if __name__ == "__main__":
    main()
