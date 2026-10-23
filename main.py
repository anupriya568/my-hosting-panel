import os
import subprocess
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8981130136:AAEgqd1m62AeJfWtauxq5Z5HYmDI207lMdA"
ADMIN_ID = 8870766171

BOT_FOLDER = "hosted_bots"
if not os.path.exists(BOT_FOLDER):
    os.makedirs(BOT_FOLDER)

running_processes = {}

def get_all_bot_files():
    files = [f for f in os.listdir(BOT_FOLDER) if f.endswith('.py')]
    return sorted(files)

def is_admin(user_id):
    return user_id == ADMIN_ID

def start_bot_process(bot_file):
    full_path = os.path.join(BOT_FOLDER, bot_file)
    log_path = os.path.join(BOT_FOLDER, f"log_{bot_file}.txt")
    
    # अगर पहले से चल रहा है तो बंद करें
    if bot_file in running_processes and running_processes[bot_file].poll() is None:
        try:
            running_processes[bot_file].terminate()
        except:
            pass
            
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(["python", full_path], stdout=log_file, stderr=log_file)
    running_processes[bot_file] = proc

def auto_start_all_bots():
    for bot_file in get_all_bot_files():
        try:
            start_bot_process(bot_file)
            print(f"Auto-started: {bot_file}")
        except Exception as e:
            print(f"Failed to auto-start {bot_file}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ माफ़ कीजिए, इस बोट का इस्तेमाल करने की अनुमति सिर्फ एडमिन को है!")
        return
    await show_panel(update.effective_chat.id, context)

async def show_panel(chat_id, context, message_id=None):
    bot_list = get_all_bot_files()
    msg = "🛡️ **Smart Hosting Panel (Button & Auto-Restart)**\n\n"
    
    if not bot_list:
        msg += "📂 फोल्डर खाली है! कोई भी `.py` फाइल सीधा यहाँ चैट में भेजें, वह ऑटोमैटिकली सेव और रन हो जाएगी।"
        keyboard = []
    else:
        msg += "📁 **अपलोडेड बॉट्स और उनके स्टेटस:**\n"
        keyboard = []
        for index, filename in enumerate(bot_list, start=1):
            is_running = filename in running_processes and running_processes[filename].poll() is None
            status_icon = "🟢 Online" if is_running else "🔴 Offline"
            msg += f"\n{index}. `{filename}` -> {status_icon}"
            
            # हर बॉट के लिए एक्शन बटन
            row = [
                InlineKeyboardButton("▶️ Run" if not is_running else "🔄 Restart", callback_data=f"run_{filename}"),
                InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{filename}"),
                InlineKeyboardButton("📋 Logs", callback_data=f"logs_{filename}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{filename}")
            ]
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔄 Refresh Panel", callback_data="refresh")])
        keyboard.append([InlineKeyboardButton("📊 Server Stats", callback_data="stats")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message_id:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=reply_markup, parse_mode="Markdown")
        except:
            pass
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ अनुमति नहीं है!", show_alert=True)
        return
        
    data = query.data
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    
    if data == "refresh":
        await query.answer("पैनल रिफ्रेश हो गया!")
        await show_panel(chat_id, context, message_id)
        
    elif data == "stats":
        ram = psutil.virtual_memory()
        total_ram = round(ram.total / (1024 * 1024), 2)
        used_ram = round(ram.used / (1024 * 1024), 2)
        cpu_percent = psutil.cpu_percent(interval=None)
        stat_msg = f"🖥️ **CPU:** `{cpu_percent}%`\n🧠 **RAM Used:** `{used_ram} MB / {total_ram} MB`"
        await query.answer(stat_msg, show_alert=True)
        
    elif data.startswith("run_"):
        bot_file = data.replace("run_", "")
        start_bot_process(bot_file)
        await query.answer(f"✅ {bot_file} शुरू/रिस्टार्ट हो गया!")
        await show_panel(chat_id, context, message_id)
        
    elif data.startswith("stop_"):
        bot_file = data.replace("stop_", "")
        if bot_file in running_processes and running_processes[bot_file].poll() is None:
            running_processes[bot_file].terminate()
            await query.answer(f"⏹️ {bot_file} बंद कर दिया गया।")
        else:
            await query.answer(f"⚠️ बोट पहले से बंद है!")
        await show_panel(chat_id, context, message_id)
        
    elif data.startswith("logs_"):
        bot_file = data.replace("logs_", "")
        log_path = os.path.join(BOT_FOLDER, f"log_{bot_file}.txt")
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                last_lines = "".join(lines[-15:])
            if not last_lines.strip():
                last_lines = "लॉग फाइल खाली है।"
            if len(last_lines) > 3500:
                last_lines = last_lines[-3500:]
            await query.message.reply_text(f"📋 **Logs for `{bot_file}`:**\n\n```text\n{last_lines}\n```", parse_mode="Markdown")
        else:
            await query.answer("❌ कोई लॉग उपलब्ध नहीं है!", show_alert=True)
            
    elif data.startswith("del_"):
        bot_file = data.replace("del_", "")
        if bot_file in running_processes and running_processes[bot_file].poll() is None:
            running_processes[bot_file].terminate()
        full_path = os.path.join(BOT_FOLDER, bot_file)
        log_path = os.path.join(BOT_FOLDER, f"log_{bot_file}.txt")
        if os.path.exists(full_path): os.remove(full_path)
        if os.path.exists(log_path): os.remove(log_path)
        await query.answer(f"🗑️ {bot_file} डिलीट हो गया!")
        await show_panel(chat_id, context, message_id)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    file = update.message.document
    if not file or not file.file_name or not file.file_name.endswith('.py'):
        await update.message.reply_text("❌ कृपया केवल `.py` फाइल भेजें!")
        return
        
    file_path = os.path.join(BOT_FOLDER, file.file_name)
    new_file = await context.bot.get_file(file.file_id)
    await new_file.download_to_drive(file_path)
    
    start_bot_process(file.file_name)
    await update.message.reply_text(f"✅ फाइल `{file.file_name}` सेव हो गई और ऑटो-रीस्टार्ट हो गई है! 🚀")
    await show_panel(update.effective_chat.id, context)

# नया जोड़ा गया /backup फीचर
async def backup_databases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ अनुमति नहीं है!")
        return
    
    # चूँकि आपके बॉट्स 'hosted_bots' फोल्डर के अंदर या सब-फोल्डर में हो सकते हैं, हम पूरे प्रोजेक्ट और होस्टेड फोल्डर दोनों में .db खोजेंगे
    search_dirs = [BOT_FOLDER, "."]
    sent_count = 0
    
    await update.message.reply_text("🔍 डेटाबेस फाइलें खोजी जा रही हैं...")
    
    found_files = set()
    for d in search_dirs:
        if os.path.exists(d):
            for root, dirs, files in os.walk(d):
                for file in files:
                    if file.endswith('.db'):
                        full_path = os.path.join(root, file)
                        found_files.add(full_path)
                        
    if not found_files:
        await update.message.reply_text("❌ सिस्टम में कोई भी `.db` फाइल नहीं मिली।")
        return
        
    for file_path in found_files:
        try:
            with open(file_path, "rb") as f:
                file_name = os.path.basename(file_path)
                await update.message.reply_document(
                    document=f,
                    caption=f"📦 Backup DB: `{file_name}`",
                    parse_mode="Markdown"
                )
            sent_count += 1
        except Exception as e:
            print(f"Error sending {file_path}: {e}")
            
    await update.message.reply_text(f"✅ कुल {sent_count} `.db` फाइलें सफलतापूर्वक आपके इनबॉक्स में भेज दी गई हैं! 🎉")

def main():
    print("Auto-starting hosted bots...")
    auto_start_all_bots()

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", start))
    app.add_handler(CommandHandler("backup", backup_databases)) # यहाँ नई कमांड जोड़ दी गई है
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Advanced Interactive Hosting Panel is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
