# ================================
# FILE: telegram_bot.py
# Telegram bot to trigger FastAPI call
# ================================

import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BASE_URL")

if not BOT_TOKEN:
    raise Exception("TELEGRAM_BOT_TOKEN not set in .env")

# ----------------
# Handlers
# ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /call to initiate a system alert call.")

async def call_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simple prompt via Telegram
    await update.message.reply_text("Enter the phone number to call:")
    # Next steps: you can add more inputs or a conversation handler
    # For demo, we hardcode:
    payload = {
        "to_number": "+1234567890",
        "company_name": "MyCompany",
        "user_name": "Client",
        "message": "This is a system update alert. Please confirm receipt.",
        "outro": "Thank you and goodbye."
    }
    try:
        r = requests.post(f"{BACKEND_URL}/start-call", json=payload, timeout=5)
        if r.ok:
            await update.message.reply_text(f"Call initiated: {r.json()}")
        else:
            await update.message.reply_text(f"Failed: {r.text}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ----------------
# Main
# ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("call", call_command))
    print("Bot started and polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
