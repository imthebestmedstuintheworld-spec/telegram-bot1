import os
import json
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

# ---------------------
# تنظیمات
# ---------------------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 6844005250  # آیدی عددی خودت
PORT = int(os.getenv("PORT", 8080))  # Render به صورت پیش‌فرض 10000 یا 8080 میده

main_menu = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"]
]

QUIZ, ADD_Q1, ADD_Q2, ADD_Q3, REMOVE_Q = range(5)

# ---------------------
# ذخیره‌سازی سؤالات و نتایج
# ---------------------
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_questions(questions):
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

def load_results():
    try:
        with open("results.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_results(results):
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# ---------------------
# هندلرها
# ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    await update.message.reply_text("سلام 👋 به منوی اصلی خوش اومدی:", reply_markup=keyboard)

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

# --- پشتیبانی ---
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    msg_info = f"📩 پیام جدید از {user.first_name} (ID: {user.id})"
    await update.message.forward(ADMIN_ID)
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg_info)
    await update.message.reply_text("✅ پیام/فایل شما برای ادمین ارسال شد.")

# ---------------------
# Flask + Webhook
# ---------------------
app = Flask(__name__)
tg_app = Application.builder().token(TOKEN).build()

# ConversationHandlers و CommandHandlers
tg_app.add_handler(CommandHandler("start", start))
conv_quiz = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📚 آزمون‌ساز$"), start_quiz)],
    states={QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
    fallbacks=[CommandHandler("start", start)],
)
tg_app.add_handler(conv_quiz)
tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_admin))

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    tg_app.update_queue.put_nowait(update)
    return "ok", 200

@app.route("/")
def home():
    return "ربات روشنه ✅"

if __name__ == "__main__":
    # آدرس وبهوک رو از Render بگیر
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=webhook_url
    )
