import json
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 6844005250

QUIZ_TIME = 120
QUIZ_LIMIT = None

main_menu = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"],
    ["⬅️ برگشت به منوی اصلی"]
]

QUIZ, CHOOSE_CATEGORY, ADD_CAT, ADD_Q1, ADD_Q2, ADD_Q3 = range(6)


# ---------- فایل ----------
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_questions(data):
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- آزمون ----------
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    if not questions:
        await update.message.reply_text("❌ هنوز هیچ دسته‌ای ثبت نشده!")
        return ConversationHandler.END

    categories = [[cat] for cat in questions.keys()]
    keyboard = ReplyKeyboardMarkup(categories, resize_keyboard=True)
    await update.message.reply_text("📂 یک دسته‌بندی انتخاب کن:", reply_markup=keyboard)
    return CHOOSE_CATEGORY

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    questions = load_questions()

    if category not in questions:
        await update.message.reply_text("❌ دسته نامعتبر بود.")
        return ConversationHandler.END

    context.user_data["category"] = category
    context.user_data["questions"] = questions[category][:QUIZ_LIMIT] if QUIZ_LIMIT else questions[category]
    context.user_data["score"] = 0
    context.user_data["q_index"] = 0
    context.user_data["quiz_active"] = True

    asyncio.create_task(quiz_timer(update, context, QUIZ_TIME))
    return await ask_question(update, context)

async def quiz_timer(update: Update, context: ContextTypes.DEFAULT_TYPE, seconds: int):
    await asyncio.sleep(seconds)
    if context.user_data.get("quiz_active"):
        context.user_data["quiz_active"] = False
        score = context.user_data.get("score", 0)
        total = len(context.user_data.get("questions", []))
        await update.message.reply_text(f"⏰ زمان آزمون تموم شد!\nنمره شما: {score}/{total}")
        return ConversationHandler.END

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data["q_index"]
    questions = context.user_data["questions"]

    if index < len(questions):
        q = questions[index]
        options = [[opt] for opt in q["options"]]
        keyboard = ReplyKeyboardMarkup(options, resize_keyboard=True)
        await update.message.reply_text(q["question"], reply_markup=keyboard)
        return QUIZ
    else:
        score = context.user_data["score"]
        total = len(questions)
        await update.message.reply_text(f"🎉 آزمون تمام شد! نمره شما: {score}/{total}")
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("quiz_active", False):
        return ConversationHandler.END

    index = context.user_data["q_index"]
    questions = context.user_data["questions"]
    q = questions[index]
    user_answer = update.message.text

    if user_answer == q["answer"]:
        context.user_data["score"] += 1
        await update.message.reply_text("✅ درست جواب دادی!")
    else:
        await update.message.reply_text(f"❌ جواب درست: {q['answer']}")

    context.user_data["q_index"] += 1
    return await ask_question(update, context)


# ---------- اضافه کردن سؤال ----------
async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه سؤال اضافه کنه!")

    questions = load_questions()
    categories = [[cat] for cat in questions.keys()] + [["➕ دسته جدید"]]
    keyboard = ReplyKeyboardMarkup(categories, resize_keyboard=True)

    await update.message.reply_text("📂 یک دسته انتخاب کن یا دسته جدید بساز:", reply_markup=keyboard)
    return ADD_CAT

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if category == "➕ دسته جدید":
        await update.message.reply_text("✍️ نام دسته جدید رو وارد کن:")
        return ADD_CAT

    context.user_data["category"] = category
    await update.message.reply_text("✍️ متن سؤال رو بنویس:")
    return ADD_Q1

async def add_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_q"] = {"question": update.message.text}
    await update.message.reply_text("🔢 گزینه‌ها رو با کاما جدا کن:")
    return ADD_Q2

async def add_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = update.message.text.split(",")
    context.user_data["new_q"]["options"] = [o.strip() for o in options]
    await update.message.reply_text("✅ جواب درست کدومه؟")
    return ADD_Q3

async def add_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = context.user_data["category"]
    q = context.user_data["new_q"]
    q["answer"] = update.message.text

    questions = load_questions()
    if category not in questions:
        questions[category] = []
    questions[category].append(q)
    save_questions(questions)

    await update.message.reply_text(f"🎉 سؤال به دسته {category} اضافه شد!")
    return ConversationHandler.END


# ---------- اجرای ربات ----------
def main():
    app = Application.builder().token(TOKEN).build()

    conv_quiz = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📚 آزمون‌ساز$"), start_quiz)],
        states={
            CHOOSE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category)],
            QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("start", start_quiz)],
    )

    conv_add = ConversationHandler(
        entry_points=[CommandHandler("addq", add_question)],
        states={
            ADD_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
            ADD_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q1)],
            ADD_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q2)],
            ADD_Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q3)],
        },
        fallbacks=[CommandHandler("start", start_quiz)],
    )

    app.add_handler(conv_quiz)
    app.add_handler(conv_add)

    port = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
