import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ====== ENV VARIABLES ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API = os.getenv("OPENROUTER_API")
CHANNEL_USERNAME = "@sheraliyev_reklama"

# ====== USER MEMORY ======
user_memory = {}

# ====== OBUNA TEKSHIRISH ======
async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ====== MENU ======
def main_menu():
    keyboard = [
        [InlineKeyboardButton("💬 AI Chat", callback_data="chat")],
        [InlineKeyboardButton("🖼 Rasm yaratish", callback_data="image")],
        [InlineKeyboardButton("🧹 Xotirani tozalash", callback_data="clear")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish",
                                  url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Tekshirish", callback_data="check")]
        ]
        await update.message.reply_text(
            "Botdan foydalanish uchun kanalga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    context.user_data["mode"] = "chat"

    await update.message.reply_text(
        "🔥 Professional AI Botga xush kelibsiz!",
        reply_markup=main_menu()
    )

# ====== BUTTONS ======
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check":
        if await check_subscription(query.from_user.id, context):
            context.user_data["mode"] = "chat"
            await query.message.reply_text("✅ Obuna tasdiqlandi!", reply_markup=main_menu())
        else:
            await query.message.reply_text("❌ Hali obuna bo‘lmagansiz!")

    elif query.data == "chat":
        context.user_data["mode"] = "chat"
        await query.message.reply_text("💬 AI Chat rejimi yoqildi.")

    elif query.data == "image":
        context.user_data["mode"] = "image"
        await query.message.reply_text("🖼 Rasm tasvirini yozing.")

    elif query.data == "clear":
        user_memory.pop(query.from_user.id, None)
        await query.message.reply_text("🧹 Xotira tozalandi!")

# ====== TEXT HANDLER ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # IMAGE MODE
    if context.user_data.get("mode") == "image":
        await generate_image(update, context)
        context.user_data["mode"] = "chat"
        return

    # CHAT MODE
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

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

    except Exception as e:
        answer = "AI javob bera olmadi."

    user_memory[user_id].append({"role": "assistant", "content": answer})

    await update.message.reply_text(answer)

# ====== IMAGE GENERATION ======
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

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/images/generations",
            headers=headers,
            json=data,
            timeout=60
        )

        result = response.json()
        image_url = result["data"][0]["url"]

        await update.message.reply_photo(photo=image_url)

    except:
        await update.message.reply_text("Rasm yaratishda xatolik.")

# ====== MAIN ======
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN qo‘yilmagan!")

    if not OPENROUTER_API:
        raise ValueError("OPENROUTER_API qo‘yilmagan!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot ishga tushdi 🚀")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
