import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("VICTORY_API_KEY")

TEAM_ID = 2733
SEASON = 2024

BASE_URL = "https://api.victoryapi.ir/football"

HEADERS = {
    "api-key": API_KEY
}

logging.basicConfig(level=logging.INFO)

def get_next_match():
    url = f"{BASE_URL}/fixtures?team={TEAM_ID}&season={SEASON}&next=1"
    response = requests.get(url, headers=HEADERS)
    return response.text  # 👈 کل خروجی API رو میفرسته

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ تست API ...")
    result = get_next_match()
    await update.message.reply_text(result[:3500])

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("next", next_match))

if __name__ == "__main__":
    app.run_polling()
