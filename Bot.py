import json
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ✅ استفاده از Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1001234567890"))
ADMINS = list(map(int, os.environ.get("ADMINS", "").split(","))) if os.environ.get("ADMINS") else []

DATA_FILE = "data.json"
MIN_DURATION = 10  # ثانیه

MESSAGES = {
    "start": {
        "fa": "🎬 به ربات تبادل فیلم خوش آمدی!",
        "en": "🎬 Welcome to the Video Exchange Bot!",
        "ar": "🎬 مرحباً بك في بوت تبادل الفيديو!"
    },
    "short": {
        "fa": "⛔ ویدئو باید حداقل ۱۰ ثانیه باشد.",
        "en": "⛔ Video must be at least 10 seconds long.",
        "ar": "⛔ يجب أن يكون الفيديو 10 ثوانٍ على الأقل."
    },
    "duplicate": {
        "fa": "❌ این ویدئو قبلاً ارسال شده.",
        "en": "❌ This video was already submitted.",
        "ar": "❌ تم إرسال هذا الفيديو مسبقاً."
    },
    "success": {
        "fa": "✅ ویدئو ثبت شد\n🎁 {count} ویدئو دریافت کردی",
        "en": "✅ Video accepted\n🎁 You received {count} videos",
        "ar": "✅ تم قبول الفيديو\n🎁 استلمت {count} فيديو"
    },
    "banned": {
        "fa": "🚫 شما بن شده‌اید.",
        "en": "🚫 You are banned.",
        "ar": "🚫 تم حظرك."
    },
    "lang_select": {
        "fa": "🌐 زبان خود را انتخاب کنید:",
        "en": "🌐 Select your language:",
        "ar": "🌐 اختر لغتك:"
    },
    "lang_set": {
        "fa": "✅ زبان ذخیره شد.",
        "en": "✅ Language saved.",
        "ar": "✅ تم حفظ اللغة."
    }
}

# ---------- داده‌ها ----------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"videos": {}, "users": {}, "banned": [], "languages": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_lang(update, data):
    uid = str(update.effective_user.id)
    if uid in data["languages"]:
        return data["languages"][uid]
    lang = update.effective_user.language_code
    return lang if lang in ["fa", "en", "ar"] else "en"

def t(key, lang, **kwargs):
    return MESSAGES[key][lang].format(**kwargs)

def is_banned(user_id, data):
    return str(user_id) in data["banned"]

# ---------- دستورات ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lang = get_lang(update, data)
    await update.message.reply_text(t("start", lang))

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lang = get_lang(update, data)

    keyboard = [[
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇸🇦 عربي", callback_data="lang_ar")
    ]]

    await update.message.reply_text(
        t("lang_select", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    uid = str(query.from_user.id)
    lang = query.data.split("_")[1]

    data["languages"][uid] = lang
    save_data(data)

    await query.edit_message_text(t("lang_set", lang))

# ---------- مدیریت ویدئو ----------
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lang = get_lang(update, data)
    user_id = str(update.effective_user.id)

    if is_banned(user_id, data):
        await update.message.reply_text(t("banned", lang))
        return

    video = update.message.video

    # ⏱ چک مدت زمان
    if video.duration < MIN_DURATION:
        await update.message.reply_text(t("short", lang))
        return

    unique_id = video.file_unique_id
    file_id = video.file_id

    if unique_id in data["videos"]:
        await update.message.reply_text(t("duplicate", lang))
        return

    data["videos"][unique_id] = file_id
    data["users"].setdefault(user_id, 0)
    data["users"][user_id] += 1

    await context.bot.send_video(
        chat_id=CHANNEL_ID,
        video=file_id
    )

    all_videos = list(data["videos"].values())
    count = data["users"][user_id]

    random_videos = random.sample(
        all_videos,
        min(count, len(all_videos))
    )

    for v in random_videos:
        await context.bot.send_video(update.effective_chat.id, v)

    save_data(data)

    await update.message.reply_text(
        t("success", lang, count=len(random_videos))
    )

# ---------- ادمین ----------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    data = load_data()
    uid = context.args[0]
    if uid not in data["banned"]:
        data["banned"].append(uid)
        save_data(data)
    await update.message.reply_text("✅ Banned")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    data = load_data()
    uid = context.args[0]
    if uid in data["banned"]:
        data["banned"].remove(uid)
        save_data(data)
    await update.message.reply_text("✅ Unbanned")

# ---------- Main ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))

    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))

    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    app.run_polling()

if __name__ == "__main__":
    main()
