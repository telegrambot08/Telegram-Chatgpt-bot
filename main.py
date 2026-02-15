import os
import requests
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API = os.getenv("OPENROUTER_API")
CHANNEL_USERNAME = "@sheraliyev_reklama"

user_memory = {}

# ===== KEEP ALIVE =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti 🚀"

def run():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()

# ===== OBUNA TEKSHIRISH =====
async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== MENU =====
def menu():
    keyboard = [
        [InlineKeyboardButton("💬 AI Chat", callback_data="chat")],
        [InlineKeyboardButton("🖼 Rasm yaratish", callback_data="image")],
        [InlineKeyboardButton("🧹 Xotirani tozalash", callback_data="clear")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Tekshirish", callback_data="check")]
        ]
        await update.message.reply_text(
            "Botdan foydalanish uchun kanalga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "🔥 Professional AI Botga xush kelibsiz!",
        reply_markup=menu()
    )

# ===== BUTTON HANDLER =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check":
        if await check_subscription(query.from_user.id, context):
            await query.message.reply_text("✅ Obuna tasdiqlandi!", reply_markup=menu())
        else:
            await query.message.reply_text("❌ Hali obuna bo‘lmagansiz!")

    elif query.data == "clear":
        user_memory.pop(query.from_user.id, None)
        await query.message.reply_text("🧹 Xotira tozalandi!")

    elif query.data == "image":
        await query.message.reply_text("Rasm tasvirini yozing...")

# ===== AI CHAT + XOTIRA =====
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({"role": "user", "content": text})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": user_memory[user_id]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()

    try:
        answer = result["choices"][0]["message"]["content"]
    except:
        answer = "Xatolik yuz berdi."

    user_memory[user_id].append({"role": "assistant", "content": answer})

    await update.message.reply_text(answer)

# ===== IMAGE GENERATION =====
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/dall-e-3",
        "prompt": prompt,
        "size": "1024x1024"
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/images/generations",
        headers=headers,
        json=data
    )

    result = response.json()

    try:
        image_url = result["data"][0]["url"]
        await update.message.reply_photo(photo=image_url)
    except:
        await update.message.reply_text("Rasm yaratishda xatolik.")

# ===== MAIN =====
def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(buttons))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    print("Bot ishga tushdi 🚀")
    app_bot.run_polling()

if __name__ == "__main__":
    main()
