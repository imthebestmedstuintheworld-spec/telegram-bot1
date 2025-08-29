import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

# متغیرها
TOKEN = os.getenv("TOKEN")   # توکن ربات از تنظیمات Render → Environment
ADMIN_ID = 6844005250        # آیدی عددی ادمین (خودت بذار)

main_menu = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"]
]

QUIZ, ADD_Q1, ADD_Q2, ADD_Q3, REMOVE_Q = range(5)

# --- مدیریت فایل سؤال‌ها ---
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_questions(questions):
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

# --- مدیریت نتایج ---
def load_results():
    try:
        with open("results.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_results(results):
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# --- شروع ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text("سلام 👋 به منوی اصلی خوش اومدی:", reply_markup=keyboard)

# --- آزمون ---
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    if not questions:
        await update.message.reply_text("❌ هنوز هیچ سؤالی ثبت نشده!")
        return ConversationHandler.END

    context.user_data["questions"] = questions
    context.user_data["score"] = 0
    context.user_data["q_index"] = 0
    return await ask_question(update, context)

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

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# --- مدیریت سؤال‌ها (ادمین) ---
async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه سؤال اضافه کنه!")
    await update.message.reply_text("✍️ متن سؤال رو بنویس:")
    return ADD_Q1

async def add_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_q"] = {"question": update.message.text}
    await update.message.reply_text("🔢 گزینه‌ها رو با کاما جدا کن (مثلاً: الف, ب, ج, د):")
    return ADD_Q2

async def add_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = update.message.text.split(",")
    context.user_data["new_q"]["options"] = [o.strip() for o in options]
    await update.message.reply_text("✅ جواب درست کدومه؟")
    return ADD_Q3

async def add_q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_q"]["answer"] = update.message.text
    questions = load_questions()
    questions.append(context.user_data["new_q"])
    save_questions(questions)
    await update.message.reply_text("🎉 سؤال با موفقیت ذخیره شد!")
    return ConversationHandler.END

async def remove_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه سؤال حذف کنه!")

    questions = load_questions()
    if not questions:
        return await update.message.reply_text("❌ هنوز هیچ سؤالی ثبت نشده!")

    msg = "📋 لیست سؤالات:\n"
    for i, q in enumerate(questions, 1):
        msg += f"{i}. {q['question']}\n"
    msg += "\n✍️ شماره سؤال برای حذف رو بفرست."
    await update.message.reply_text(msg)
    return REMOVE_Q

async def remove_q_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        index = int(update.message.text) - 1
        questions = load_questions()
        removed = questions.pop(index)
        save_questions(questions)
        await update.message.reply_text(f"🗑 سؤال حذف شد: {removed['question']}")
    except:
        await update.message.reply_text("❌ شماره نامعتبر بود!")
    return ConversationHandler.END

# --- نتایج ---
async def results_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه نتایج رو ببینه!")

    results = load_results()
    if not results:
        return await update.message.reply_text("❌ هنوز هیچ نتیجه‌ای ثبت نشده!")

    msg = "📊 نتایج آزمون:\n\n"
    for uid, data in results.items():
        msg += f"{data['name']} → {data['score']}/{data['total']}\n"

    await update.message.reply_text(msg)

async def my_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    results = load_results()

    if user_id not in results:
        await update.message.reply_text("❌ شما هنوز هیچ آزمونی نداده‌اید.")
    else:
        data = results[user_id]
        await update.message.reply_text(
            f"📋 نتیجه آخرین آزمون شما:\n\n"
            f"نام: {data['name']}\n"
            f"نمره: {data['score']} / {data['total']}"
        )

# --- پشتیبانی ---
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    msg_info = f"📩 پیام جدید از {user.first_name} (ID: {user.id})"

    # فوروارد پیام/فایل به ادمین
    await update.message.forward(ADMIN_ID)
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg_info)

    # تایید به کاربر
    await update.message.reply_text("✅ پیام/فایل شما برای ادمین ارسال شد.")

# ادمین جواب بده
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        return await update.message.reply_text("❌ فرمت درست: /reply <user_id> <متن پیام>")

    user_id = int(context.args[0])
    reply_text = " ".join(context.args[1:])
    await context.bot.send_message(chat_id=user_id, text=f"📬 پاسخ ادمین:\n\n{reply_text}")
    await update.message.reply_text("✅ پیام برای کاربر ارسال شد.")

# --- سایر پیام‌ها ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📚 آزمون‌ساز":
        return await start_quiz(update, context)
    elif text == "📂 فایل‌ها":
        await update.message.reply_text("📂 می‌تونی فایل بفرستی تا مستقیم به ادمین ارسال بشه.")
    elif text == "💳 خرید":
        await update.message.reply_text("برای خرید به درگاه وصلت می‌کنم 💳")
    elif text == "🛠 پشتیبانی":
        await update.message.reply_text("پیامت رو بفرست، مستقیم به ادمین می‌رسه 🛠")
    else:
        keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        await update.message.reply_text("منوی اصلی:", reply_markup=keyboard)

# --- اجرای ربات (Render) ---
def main():
    app = Application.builder().token(TOKEN).build()

    # مدیریت آزمون‌ها
    conv_quiz = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📚 آزمون‌ساز$"), start_quiz)],
        states={QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    )

    conv_add = ConversationHandler(
        entry_points=[CommandHandler("addq", add_question)],
        states={
            ADD_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q1)],
            ADD_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q2)],
            ADD_Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_q3)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    conv_remove = ConversationHandler(
        entry_points=[CommandHandler("removeq", remove_question)],
        states={REMOVE_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_q_done)]},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_quiz)
    app.add_handler(conv_add)
    app.add_handler(conv_remove)
    app.add_handler(CommandHandler("results", results_cmd))
    app.add_handler(CommandHandler("myresult", my_result))
    app.add_handler(CommandHandler("reply", reply_to_user))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # اجرای وب‌هوک مخصوص Render
    PORT = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
