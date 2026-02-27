import os
import json
import logging
import requests
import pytz
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
TEAM_NAME = "Esteghlal"

logging.basicConfig(level=logging.INFO)

IRAN_TZ = pytz.timezone("Asia/Tehran")
USERS_FILE = "users.json"
SENT_FILE = "sent_notifications.json"

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

def get_next_match():
    search_url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={TEAM_NAME}"
    team_res = requests.get(search_url, timeout=10).json()

    if not team_res.get("teams"):
        return None

    team_id = team_res["teams"][0]["idTeam"]

    events_url = f"https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}"
    events_res = requests.get(events_url, timeout=10).json()

    events = events_res.get("events")
    if not events:
        return None

    event = events[0]

    utc_time = datetime.strptime(
        f"{event['dateEvent']} {event['strTime']}",
        "%Y-%m-%d %H:%M:%S"
    )
    utc_time = pytz.utc.localize(utc_time)
    iran_time = utc_time.astimezone(IRAN_TZ)

    return {
        "id": event["idEvent"],
        "title": event["strEvent"],
        "time": iran_time
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_chat.id)
    await update.message.reply_text("🔥 یادآور بازی‌های استقلال فعال شد")

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = get_next_match()

    if not match:
        await update.message.reply_text("⛔ فعلاً بازی آینده‌ای ثبت نشده")
        return

    await update.message.reply_text(
        f"⚽ بازی بعدی استقلال:\n\n"
        f"{match['title']}\n"
        f"🗓 {match['time'].strftime('%Y-%m-%d')}\n"
        f"⏰ {match['time'].strftime('%H:%M')} (ایران)"
    )

async def check_reminder(context: ContextTypes.DEFAULT_TYPE):
    match = get_next_match()
    if not match:
        return

    sent = load_json(SENT_FILE)
    now = datetime.now(IRAN_TZ)
    diff = match["time"] - now
    match_id = match["id"]

    if timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30):
        key = match_id + "_24h"
        if key not in sent:
            for user in get_users():
                await context.bot.send_message(
                    chat_id=user,
                    text=f"⏳ فردا ساعت {match['time'].strftime('%H:%M')} (ایران)\n{match['title']}"
                )
            sent[key] = True

    if timedelta(minutes=50) < diff < timedelta(minutes=70):
        key = match_id + "_1h"
        if key not in sent:
            for user in get_users():
                await context.bot.send_message(
                    chat_id=user,
                    text=f"🔥 یک ساعت تا بازی!\n{match['title']}\n🕒 {match['time'].strftime('%H:%M')} (ایران)"
                )
            sent[key] = True

    save_json(SENT_FILE, sent)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_match))
    app.job_queue.run_repeating(check_reminder, interval=1800, first=10)
    app.run_polling()
