import os
import json
import logging
import requests
import pytz
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

logging.basicConfig(level=logging.INFO)

IRAN_TZ = pytz.timezone("Asia/Tehran")

USERS_FILE = "users.json"
SENT_FILE = "sent_notifications.json"
CACHE_FILE = "fixtures_cache.json"

TEAM_ID = 3402  # Esteghlal Tehran (API-Football ID)

HEADERS = {
    "x-apisports-key": API_KEY
}

# ---------- Utility ----------

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def add_user(chat_id):
    users = load_json(USERS_FILE)
    users[str(chat_id)] = True
    save_json(USERS_FILE, users)

def get_users():
    return load_json(USERS_FILE).keys()

# ---------- API + CACHE ----------

def get_fixtures():
    cache = load_json(CACHE_FILE)
    now = datetime.utcnow()

    if cache and "timestamp" in cache:
        cached_time = datetime.fromisoformat(cache["timestamp"])
        if now - cached_time < timedelta(minutes=15):
            return cache["data"]

    url = f"https://v3.football.api-sports.io/fixtures?team={TEAM_ID}&next=5"
    res = requests.get(url, headers=HEADERS, timeout=15)
    data = res.json()

    fixtures = data.get("response", [])

    save_json(CACHE_FILE, {
        "timestamp": now.isoformat(),
        "data": fixtures
    })

    return fixtures

def get_next_match():
    fixtures = get_fixtures()
    if not fixtures:
        return None

    fixture = fixtures[0]

    utc_time = datetime.fromisoformat(
        fixture["fixture"]["date"].replace("Z", "+00:00")
    )

    iran_time = utc_time.astimezone(IRAN_TZ)

    return {
        "id": str(fixture["fixture"]["id"]),
        "title": f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}",
        "time": iran_time,
        "status": fixture["fixture"]["status"]["short"],
        "score": fixture["goals"]
    }

# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_chat.id)
    await update.message.reply_text("🔥 یادآور حرفه‌ای بازی‌های استقلال فعال شد")

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = get_next_match()

    if not match:
        await update.message.reply_text("⛔ بازی آینده‌ای ثبت نشده")
        return

    await update.message.reply_text(
        f"⚽ بازی بعدی استقلال:\n\n"
        f"{match['title']}\n"
        f"🗓 {match['time'].strftime('%Y-%m-%d')}\n"
        f"⏰ {match['time'].strftime('%H:%M')} (ایران)"
    )

# ---------- Reminder Engine ----------

async def check_matches(context: ContextTypes.DEFAULT_TYPE):
    match = get_next_match()
    if not match:
        return

    sent = load_json(SENT_FILE)
    now = datetime.now(IRAN_TZ)
    diff = match["time"] - now
    match_id = match["id"]

    # 24h reminder
    if timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30):
        key = match_id + "_24h"
        if key not in sent:
            for user in get_users():
                await context.bot.send_message(
                    chat_id=user,
                    text=f"⏳ فردا بازی استقلال!\n\n{match['title']}\n🕒 {match['time'].strftime('%H:%M')} (ایران)"
                )
            sent[key] = True

    # 1h reminder
    if timedelta(minutes=50) < diff < timedelta(minutes=70):
        key = match_id + "_1h"
        if key not in sent:
            for user in get_users():
                await context.bot.send_message(
                    chat_id=user,
                    text=f"🔥 یک ساعت تا بازی!\n\n{match['title']}\n🕒 {match['time'].strftime('%H:%M')} (ایران)"
                )
            sent[key] = True

    # Result
    if match["status"] == "FT":
        key = match_id + "_result"
        if key not in sent:
            score = match["score"]
            for user in get_users():
                await context.bot.send_message(
                    chat_id=user,
                    text=f"🏁 نتیجه بازی:\n\n{match['title']}\n⚽ {score['home']} - {score['away']}"
                )
            sent[key] = True

    save_json(SENT_FILE, sent)

# ---------- Main ----------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_match))
    app.job_queue.run_repeating(check_matches, interval=1800, first=15)
    app.run_polling()
