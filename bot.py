import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

# ---- تنظیمات ----
TOKEN = os.getenv("TOKEN")  # توکن از Environment (Render)
ADMIN_ID = 6844005250       # آیدی عددی ادمین
CHANNEL = "@top1edu"        # کانال عضویت اجباری
GROUP = "@novakonkur"       # گروه عضویت اجباری

# ---- متغیرهای قابل تنظیم توسط ادمین ----
QUIZ_TIME = 120      # زمان آزمون (ثانیه) – پیش‌فرض ۲ دقیقه
QUIZ_LIMIT = None    # تعداد سؤالات – None یعنی همه سؤالات

# ---- منو ----
main_menu = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"],
    ["⬅️ برگشت به منوی اصلی"]
]

QUIZ, ADD_Q1, ADD_Q2, ADD_Q3, REMOVE_Q = range(5)

# ---- فایل مدیریت سؤالات ----
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_questions(questions):
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

# ---- فایل مدیریت نتایج ----
def load_results():
    try:
        with open("results.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_results(results):
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# ---- شروع ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text("سلام 👋 به منوی اصلی خوش اومدی:", reply_markup=keyboard)

# ---- آزمون ----
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    if not questions:
        await update.message.reply_text("❌ هنوز هیچ سؤالی ثبت نشده!")
        return ConversationHandler.END

    # در نظر گرفتن محدودیت تعداد سؤالات
    selected_questions = questions[:QUIZ_LIMIT] if QUIZ_LIMIT else questions

    context.user_data["questions"] = selected_questions
    context.user_data["score"] = 0
    context.user_data["q_index"] = 0
    context.user_data["quiz_active"] = True

    # تایمر کل آزمون
    asyncio.create_task(quiz_timer(update, context, QUIZ_TIME))

    return await ask_question(update, context)

async def quiz_timer(update: Update, context: ContextTypes.DEFAULT_TYPE, seconds: int):
    await asyncio.sleep(seconds)
    if context.user_data.get("quiz_active"):
        context.user_data["quiz_active"] = False
        score = context.user_data.get("score", 0)
        total = len(context.user_data.get("questions", []))
        await update.message.reply_text(
            f"⏰ زمان آزمون تموم شد!\nنمره شما: {score}/{total}"
        )
        return ConversationHandler.END

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("quiz_active", False):
        return ConversationHandler.END

    index = context.user_data["q_index"]
    questions = context.user_data["questions"]

    if index < len(questions):
        q = questions[index]
        options = [[opt] for opt in q["options"]]
        keyboard = ReplyKeyboardMarkup(options, resize_keyboard=True)
        await update.message.reply_text(q["question"], reply_markup=keyboard)
        return QUIZ
    else:
        return await finish_quiz(update, context)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("quiz_active", False):
        return ConversationHandler.END

    index = context.user_data["q_index"]
    questions = context.user_data["questions"]

    if index < len(questions):
        q = questions[index]
        user_answer = update.message.text
        if user_answer == q["answer"]:
            context.user_data["score"] += 1
            await update.message.reply_text("✅ درست جواب دادی!")
        else:
            await update.message.reply_text(f"❌ جواب درست: {q['answer']}")

        context.user_data["q_index"] += 1
        return await ask_question(update, context)
    else:
        return await finish_quiz(update, context)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quiz_active"] = False
    score = context.user_data["score"]
    total = len(context.user_data["questions"])
    await update.message.reply_text(f"🎉 آزمون تمام شد! نمره شما: {score}/{total}")

    # ذخیره نتیجه
    results = load_results()
    user_id = str(update.message.from_user.id)
    results[user_id] = {
        "name": update.message.from_user.first_name,
        "score": score,
        "total": total
    }
    save_results(results)

    return ConversationHandler.END

# ---- دستورات مدیریتی برای ادمین ----
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QUIZ_TIME
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه اینو تغییر بده!")
    if not context.args:
        return await update.message.reply_text("❌ فرمت درست: /settime <زمان به ثانیه>")
    try:
        QUIZ_TIME = int(context.args[0])
        await update.message.reply_text(f"✅ زمان آزمون روی {QUIZ_TIME} ثانیه تنظیم شد.")
    except:
        await update.message.reply_text("❌ مقدار نامعتبره!")

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QUIZ_LIMIT
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه اینو تغییر بده!")
    if not context.args:
        return await update.message.reply_text("❌ فرمت درست: /setlimit <تعداد سوال>")
    try:
        val = int(context.args[0])
        QUIZ_LIMIT = None if val <= 0 else val
        msg = "همه سؤالات" if QUIZ_LIMIT is None else f"{QUIZ_LIMIT} سؤال"
        await update.message.reply_text(f"✅ تعداد سؤالات روی {msg} تنظیم شد.")
    except:
        await update.message.reply_text("❌ مقدار نامعتبره!")

# ---- دکمه برگشت ----
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text("🔙 برگشتی به منوی اصلی", reply_markup=keyboard)

# ---- اجرای ربات روی Render ----
def main():
    app = Application.builder().token(TOKEN).build()

    # ConversationHandlers
    conv_quiz = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📚 آزمون‌ساز$"), start_quiz)],
        states={QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settime", set_time))
    app.add_handler(CommandHandler("setlimit", set_limit))
    app.add_handler(MessageHandler(filters.Regex("^⬅️ برگشت به منوی اصلی$"), go_back))
    app.add_handler(conv_quiz)

    # اجرای وب‌هوک (ویژه Render)
    PORT = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
