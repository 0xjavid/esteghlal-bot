import os
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
TEAM_ID = 2664
BASE_URL = "https://v3.football.api-sports.io/fixtures"

logging.basicConfig(level=logging.INFO)

USERS_FILE = "users.json"
SENT_FILE = "sent_notifications.json"

CACHE = {"data": None, "last_update": None}
CACHE_DURATION = timedelta(minutes=30)

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def add_user(chat_id):
    users = load_json(USERS_FILE)
    users[str(chat_id)] = True
    save_json(USERS_FILE, users)

def get_users():
    return load_json(USERS_FILE).keys()

def get_matches():
    now = datetime.now(timezone.utc)
    if CACHE["data"] and CACHE["last_update"]:
        if now - CACHE["last_update"] < CACHE_DURATION:
            return CACHE["data"]

    headers = {"x-apisports-key": API_KEY}
    params = {"team": TEAM_ID, "next": 20}

    response = requests.get(BASE_URL, headers=headers, params=params)
    data = response.json()

    matches = data.get("response", [])
    CACHE["data"] = matches
    CACHE["last_update"] = now
    return matches

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_chat.id)
    await update.message.reply_text("ربات یادآور استقلال فعال شد ✅")

async def check_matches(context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()
    sent = load_json(SENT_FILE)
    now = datetime.now(timezone.utc)

    for match in matches:
        fixture = match["fixture"]
        teams = match["teams"]
        goals = match["goals"]
        fixture_id = str(fixture["id"])

        match_time = datetime.fromisoformat(
            fixture["date"].replace("Z", "+00:00")
        )

        diff = match_time - now
        status = fixture["status"]["short"]

        opponent = (
            teams["away"]["name"]
            if teams["home"]["id"] == TEAM_ID
            else teams["home"]["name"]
        )

        if timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30):
            key = fixture_id + "_24h"
            if key not in sent:
                for user in get_users():
                    await context.bot.send_message(
                        chat_id=user,
                        text=f"⏳ فردا ساعت {match_time.strftime('%H:%M')} با {opponent}"
                    )
                sent[key] = True

        if timedelta(minutes=50) < diff < timedelta(minutes=70):
            key = fixture_id + "_1h"
            if key not in sent:
                for user in get_users():
                    await context.bot.send_message(
                        chat_id=user,
                        text=f"🔥 یک ساعت تا بازی با {opponent}"
                    )
                sent[key] = True

        if status == "FT":
            key = fixture_id + "_FT"
            if key not in sent:
                for user in get_users():
                    await context.bot.send_message(
                        chat_id=user,
                        text=f"🏁 نتیجه: {teams['home']['name']} {goals['home']} - {goals['away']} {teams['away']['name']}"
                    )
                sent[key] = True

    save_json(SENT_FILE, sent)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.job_queue.run_repeating(check_matches, interval=1800, first=10)

PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.getenv("RAILWAY_STATIC_URL")

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"https://{WEBHOOK_URL}"
)
