import os
import json
import logging
import feedparser
import pytz
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

USERS_FILE = "users.json"
SENT_FILE = "sent_notifications.json"

IRAN_TZ = pytz.timezone("Asia/Tehran")
RSS_URL = "https://www.sofascore.com/team/football/esteghlal/3402/rss"

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
    feed = feedparser.parse(RSS_URL)
    matches = []

    for entry in feed.entries:
        try:
            match_time_utc = datetime(*entry.published_parsed[:6])
            match_time_utc = pytz.utc.localize(match_time_utc)
            match_time_iran = match_time_utc.astimezone(IRAN_TZ)

            matches.append({
                "id": entry.id,
                "title": entry.title,
                "time": match_time_iran
            })
        except:
            continue

    return matches

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_chat.id)
    await update.message.reply_text("🔥 یادآور بازی‌های استقلال فعال شد")

async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()
    if not matches:
        await update.message.reply_text("⛔ بازی آینده‌ای پیدا نشد")
        return

    next_game = sorted(matches, key=lambda x: x["time"])[0]
    await update.message.reply_text(
        f"⚽ بازی بعدی استقلال:\n\n"
        f"{next_game['title']}\n"
        f"🗓 {next_game['time'].strftime('%Y-%m-%d')}\n"
        f"⏰ {next_game['time'].strftime('%H:%M')} (ایران)"
    )

async def check_matches(context: ContextTypes.DEFAULT_TYPE):
    matches = get_matches()
    sent = load_json(SENT_FILE)
    now = datetime.now(IRAN_TZ)

    for match in matches:
        match_time = match["time"]
        diff = match_time - now
        fixture_id = match["id"]

        if timedelta(hours=23, minutes=30) < diff < timedelta(hours=24, minutes=30):
            key = fixture_id + "_24h"
            if key not in sent:
                for user in get_users():
                    await context.bot.send_message(
                        chat_id=user,
                        text=f"⏳ فردا ساعت {match_time.strftime('%H:%M')} (ایران)\n{match['title']}"
                    )
                sent[key] = True

        if timedelta(minutes=50) < diff < timedelta(minutes=70):
            key = fixture_id + "_1h"
            if key not in sent:
                for user in get_users():
                    await context.bot.send_message(
                        chat_id=user,
                        text=f"🔥 یک ساعت تا بازی!\n{match['title']}\n🕒 {match_time.strftime('%H:%M')} (ایران)"
                    )
                sent[key] = True

    save_json(SENT_FILE, sent)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_match))
    app.job_queue.run_repeating(check_matches, interval=1800, first=10)
    app.run_polling()
