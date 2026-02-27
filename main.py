import os
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("VICTORY_API_KEY")

TEAM_ID = 2733
SEASON = 2024

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

logging.basicConfig(level=logging.INFO)

def get_next_match():
    try:
        url = f"{BASE_URL}/fixtures?team={TEAM_ID}&season={SEASON}&next=1"
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()

        fixtures = data.get("response", [])

        if not fixtures:
            return "⛔ بازی آینده‌ای ثبت نشده"

        match = fixtures[0]

        utc_time = datetime.fromisoformat(
            match["fixture"]["date"].replace("Z", "+00:00")
        )
        iran_time = utc_time.astimezone(ZoneInfo("Asia/Tehran"))

        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        league = match["league"]["name"]

        return (
            f"🔵 بازی بعدی استقلال\n\n"
            f"🏆 {league}\n"
            f"{home} 🆚 {away}\n\n"
            f"🗓 {iran_time.strftime('%Y-%m-%d')}\n"
            f"⏰ {iran_time.strftime('%H:%M')} (ایران)"
        )

    except Exception:
        return "⚠️ خطا در دریافت اطلاعات"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 یادآور حرفه‌ای استقلال فعال شد")

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ در حال بررسی...")
    result = get_next_match()
    await update.message.reply_text(result)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("next", next_match))

if __name__ == "__main__":
    app.run_polling()
