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

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API = os.getenv("OPENROUTER_API")
CHANNEL_USERNAME = "@sheraliyev_reklama"

user_memory = {}

# ================= SUB CHECK =================
async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= MENU =================
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("💬 GPT-4o Chat", callback_data="chat"),
            InlineKeyboardButton("🎨 Ultra Real Rasm", callback_data="image")
        ],
        [InlineKeyboardButton("🧹 Xotirani tozalash", callback_data="clear")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================
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
        "🔥 GPT-4o Ultra AI Botga xush kelibsiz!",
        reply_markup=main_menu()
    )

# ================= BUTTONS =================
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
        await query.message.reply_text("🧠 GPT-4o rejimi yoqildi.")

    elif query.data == "image":
        context.user_data["mode"] = "image"
        await query.message.reply_text("🎨 Ultra realistik rasm tasvirini yozing.")

    elif query.data == "clear":
        user_memory.pop(query.from_user.id, None)
        await query.message.reply_text("🧹 Xotira tozalandi!")

# ================= PHOTO HANDLER =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    file_path = f"user_{user_id}.jpg"
    await file.download_to_drive(file_path)

    context.user_data["last_image"] = file_path

    await update.message.reply_text(
        "📸 Rasm qabul qilindi.\nEndi nima qo‘shishni yozing."
    )

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # IMAGE EDIT MODE
    if "last_image" in context.user_data:
        await edit_image(update, context)
        return

    # IMAGE GENERATION MODE
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
        "model": "openai/gpt-4o",
        "messages": user_memory[user_id],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=90
        )

        result = response.json()

        if "choices" not in result:
            await update.message.reply_text(str(result))
            return

        answer = result["choices"][0]["message"]["content"]

    except Exception as e:
        answer = f"❌ GPT javob bera olmadi:\n{e}"

    user_memory[user_id].append({"role": "assistant", "content": answer})
    await update.message.reply_text(answer)

# ================= IMAGE GENERATION =================
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    ultra_prompt = f"Ultra realistic, 8k, cinematic lighting, detailed, professional photography, {prompt}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/dall-e-3",
        "prompt": ultra_prompt,
        "size": "1024x1024"
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/images/generations",
            headers=headers,
            json=data,
            timeout=120
        )

        result = response.json()

        if "data" not in result:
            await update.message.reply_text(str(result))
            return

        image_url = result["data"][0]["url"]
        await update.message.reply_photo(photo=image_url)

    except Exception as e:
        await update.message.reply_text(f"❌ Rasm yaratishda xatolik:\n{e}")

# ================= IMAGE EDIT =================
async def edit_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    image_path = context.user_data.get("last_image")

    ultra_prompt = f"Ultra realistic seamless edit, same lighting, same angle, same perspective, {prompt}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API}"
    }

    try:
        with open(image_path, "rb") as img:

            response = requests.post(
                "https://openrouter.ai/api/v1/images/edits",
                headers=headers,
                files={"image": img},
                data={
                    "model": "openai/dall-e-3",
                    "prompt": ultra_prompt,
                    "size": "1024x1024"
                },
                timeout=120
            )

        result = response.json()

        if "data" not in result:
            await update.message.reply_text(str(result))
            return

        image_url = result["data"][0]["url"]
        await update.message.reply_photo(photo=image_url)

        os.remove(image_path)
        context.user_data.pop("last_image")

    except Exception as e:
        await update.message.reply_text(f"❌ Rasmni tahrirlashda xatolik:\n{e}")

# ================= MAIN =================
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN qo‘yilmagan!")

    if not OPENROUTER_API:
        raise ValueError("OPENROUTER_API qo‘yilmagan!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🔥 GPT-4o Ultra Bot ishga tushdi 🚀")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
