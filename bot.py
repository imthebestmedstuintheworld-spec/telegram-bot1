import json
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

# -------- تنظیمات اصلی --------
TOKEN = os.getenv("TOKEN")  # از Render می‌گیره
ADMIN_ID = 6844005250       # آیدی عددی ادمین

# تنظیمات آزمون (قابل تغییر با دستورات ادمین)
QUIZ_TIME = 120      # زمان آزمون (ثانیه)
QUIZ_LIMIT = None    # تعداد سؤالات (None = همه)

# منوی اصلی
main_menu = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"],
    ["⬅️ برگشت به منوی اصلی"]
]

QUIZ, ADD_Q1, ADD_Q2, ADD_Q3, REMOVE_Q = range(5)


# -------- مدیریت فایل سؤال‌ها --------
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_questions(questions):
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


# -------- مدیریت نتایج --------
def load_results():
    try:
        with open("results.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_results(results):
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# -------- مدیریت ریفرال --------
def load_referrals():
    try:
        with open("referrals.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_referrals(data):
    with open("referrals.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------- استارت --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args  # اگر با لینک دعوت اومده
    user_id = str(update.message.from_user.id)
    referrals = load_referrals()

    if args:
        inviter_id = args[0]
        if inviter_id != user_id:
            referrals.setdefault(inviter_id, {"count": 0, "users": []})
            if user_id not in referrals[inviter_id]["users"]:
                referrals[inviter_id]["users"].append(user_id)
                referrals[inviter_id]["count"] += 1
                save_referrals(referrals)
                await update.message.reply_text("✅ ورود شما با لینک دعوت ثبت شد.")

    keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text("سلام 👋 به منوی اصلی خوش اومدی:", reply_markup=keyboard)


# -------- آزمون --------
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    if not questions:
        await update.message.reply_text("❌ هنوز هیچ سؤالی ثبت نشده!")
        return ConversationHandler.END

    context.user_data["questions"] = questions[:QUIZ_LIMIT] if QUIZ_LIMIT else questions
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


# -------- مدیریت سؤال‌ها (ادمین) --------
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


# -------- نتایج --------
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
        await update.message.reply_text(f"📋 نتیجه آخرین آزمون شما:\n\n"
                                        f"نام: {data['name']}\n"
                                        f"نمره: {data['score']} / {data['total']}")


# -------- ریفرال --------
async def my_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    referrals = load_referrals()
    if user_id not in referrals:
        await update.message.reply_text("❌ شما هنوز کسی رو دعوت نکردید.")
    else:
        count = referrals[user_id]["count"]
        await update.message.reply_text(
            f"📊 تعداد دعوتی‌های شما: {count}\n"
            f"🔗 لینک شما: https://t.me/top1edu_bot?start={user_id}"
        )


# -------- اجرای ربات --------
def main():
    app = Application.builder().token(TOKEN).build()

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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_quiz)
    app.add_handler(conv_add)
    app.add_handler(CommandHandler("results", results_cmd))
    app.add_handler(CommandHandler("myresult", my_result))
    app.add_handler(CommandHandler("myreferrals", my_referrals))

    # حالت webhook (مناسب Render)
    port = int(os.environ.get("PORT", 8080))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
