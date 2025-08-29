import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)

# --- ثابت‌ها ---
TOKEN = "8420390679:AAFPVWlS826ibp5wecd0IQg2afbosoTBSNU"
ADMIN_ID = 6844005250

CHANNEL_ID = "@top1edu"     # کانال اجباری
GROUP_ID   = "@novakonkur"  # گروه اجباری

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT,
                  options TEXT,
                  answer TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (user_id INTEGER,
                  name TEXT,
                  score INTEGER,
                  total INTEGER)''')
    conn.commit()
    conn.close()

def get_questions_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM questions")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "question": r[1], "options": r[2].split(","), "answer": r[3]} for r in rows]

def delete_question_db(qid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit()
    conn.close()

def save_result_db(user_id, name, score, total):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM results WHERE user_id=?", (user_id,))
    c.execute("INSERT INTO results (user_id, name, score, total) VALUES (?, ?, ?, ?)",
              (user_id, name, score, total))
    conn.commit()
    conn.close()

def get_results_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM results")
    rows = c.fetchall()
    conn.close()
    return rows

# --- منوها ---
main_menu_user = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"]
]

main_menu_admin = [
    ["📚 آزمون‌ساز", "📂 فایل‌ها"],
    ["💳 خرید", "🛠 پشتیبانی"],
    ["📋 لیست سوالات"]
]

back_menu = [["🔙 بازگشت"]]

QUIZ, SUPPORT = range(2)

# --- چک عضویت اجباری ---
async def check_membership(user_id, context):
    try:
        member1 = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        member2 = await context.bot.get_chat_member(GROUP_ID, user_id)
        if member1.status in ["member", "administrator", "creator"] and member2.status in ["member", "administrator", "creator"]:
            return True
        return False
    except:
        return False

# --- شروع ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_member = await check_membership(user_id, context)

    if not is_member:
        return await update.message.reply_text(
            "❌ برای استفاده از ربات باید عضو شوید:\n\n"
            f"📢 کانال: {CHANNEL_ID}\n👥 گروه: {GROUP_ID}"
        )

    if user_id == ADMIN_ID:
        keyboard = ReplyKeyboardMarkup(main_menu_admin, resize_keyboard=True)
    else:
        keyboard = ReplyKeyboardMarkup(main_menu_user, resize_keyboard=True)
    await update.message.reply_text("سلام 👋 به منوی اصلی خوش اومدی:", reply_markup=keyboard)

# --- پشتیبانی ---
async def support_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(back_menu, resize_keyboard=True)
    await update.message.reply_text("✍️ پیام خود را بنویسید و ارسال کنید:", reply_markup=keyboard)
    return SUPPORT

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler

    if update.message.text == "🔙 بازگشت":
        await start(update, context)
        return ConversationHandler.END   # ✅ مهم: خروج کامل از حالت SUPPORT

    user = update.message.from_user
    await update.message.forward(ADMIN_ID)
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 پیام از {user.first_name} (ID: {user.id})")
    await update.message.reply_text("✅ پیام شما به ادمین ارسال شد.")
    return SUPPORT

# --- فایل‌ها ---
async def files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 اینجا بخش فایل‌هاست. (بعداً قابلیت آپلود/دانلود اضافه می‌کنیم)")

# --- خرید ---
async def buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 برای خرید وارد لینک زیر شوید:\nhttps://zarinp.al/yourlink")

# --- آزمون ---
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = get_questions_db()
    if not questions:
        return await update.message.reply_text("❌ هنوز هیچ سؤالی ثبت نشده!")

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
        keyboard = ReplyKeyboardMarkup(options + [["🔙 بازگشت"]], resize_keyboard=True)
        await update.message.reply_text(q["question"], reply_markup=keyboard)
        return QUIZ
    else:
        score = context.user_data["score"]
        total = len(questions)
        await update.message.reply_text(f"🎉 آزمون تمام شد! نمره شما: {score}/{total}")
        save_result_db(update.message.from_user.id, update.message.from_user.first_name, score, total)
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 بازگشت":
        await start(update, context)
        return ConversationHandler.END  # ✅ برگرد به منوی اصلی و آزمون هم تموم بشه

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

# --- لیست سوالات ---
async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تواند سوالات را ببیند.")

    questions = get_questions_db()
    if not questions:
        return await update.message.reply_text("❌ هیچ سوالی ثبت نشده است.")

    for q in questions:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 حذف", callback_data=f"del_{q['id']}")]
        ])
        await update.message.reply_text(f"{q['id']}. {q['question']}", reply_markup=keyboard)

async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qid = int(query.data.split("_")[1])
    delete_question_db(qid)
    await query.edit_message_text("🗑 سوال حذف شد.")

# --- نتایج ---
async def results_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ فقط ادمین می‌تونه نتایج رو ببینه!")

    results = get_results_db()
    if not results:
        return await update.message.reply_text("❌ هنوز هیچ نتیجه‌ای ثبت نشده!")

    msg = "📊 نتایج آزمون:\n\n"
    for r in results:
        msg += f"{r[1]} → {r[2]}/{r[3]}\n"
    await update.message.reply_text(msg)

async def my_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    results = get_results_db()
    for r in results:
        if r[0] == user_id:
            return await update.message.reply_text(
                f"📋 نتیجه آخرین آزمون شما:\n\n"
                f"نام: {r[1]}\n"
                f"نمره: {r[2]} / {r[3]}"
            )
    await update.message.reply_text("❌ شما هنوز هیچ آزمونی نداده‌اید.")

# --- اجرای ربات ---
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv_support = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛠 پشتیبانی$"), support_entry)],
        states={SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)]},
        fallbacks=[CommandHandler("start", start)],
    )

    conv_quiz = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📚 آزمون‌ساز$"), start_quiz)],
        states={QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("results", results_cmd))
    app.add_handler(CommandHandler("myresult", my_result))
    app.add_handler(conv_support)
    app.add_handler(conv_quiz)
    app.add_handler(CallbackQueryHandler(delete_question, pattern="^del_"))
    app.add_handler(MessageHandler(filters.Regex("^📂 فایل‌ها$"), files_menu))
    app.add_handler(MessageHandler(filters.Regex("^💳 خرید$"), buy_menu))

    app.run_polling()

if __name__ == "__main__":
    main()
