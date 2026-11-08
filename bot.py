import telebot
from telebot import types
import requests
import json
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

Thread(target=run_web, daemon=True).start()

BOT_TOKEN = "9109756671:AAHHDN2X-Xuo5ywTJQ7spy1Bc6NJhn4_K1Q"
ADMIN_ID = 7376984711
VOLTX_API_KEY = "MKWWPCL28GS"
BASE_URL = "https://2oo9.cloud"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=15)
session = requests.Session()
HEADERS = {"mauthapi": VOLTX_API_KEY, "Content-Type": "application/json"}

DATA_FILE = "bot_db.json"
db = {"users": {}, "services": [], "reward": 0.02}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            db = json.load(f)
    except Exception:
        pass

def save_db():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f)

def get_bal(uid):
    u = str(uid)
    if u not in db["users"]:
        db["users"][u] = 0.0
        save_db()
    return db["users"][u]

def add_bal(uid, amt):
    u = str(uid)
    db["users"][u] = round(get_bal(uid) + amt, 4)
    save_db()

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📱 Buy Number", "💰 Balance")
    markup.row("💳 Deposit", "💸 Withdraw")
    markup.row("👤 My Profile")
    if uid == ADMIN_ID:
        markup.row("⚙️ Admin Panel")
    return markup

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    get_bal(uid)
    rew = db.get("reward", 0.02)
    bot.send_message(msg.chat.id, f"👋 স্বাগতম {msg.from_user.first_name}!\n\n🎁 প্রতিটি সফল OTP রিসিভে পাচ্ছেন **${rew:.2f}** বোনাস!\nনিচের মেনু থেকে অপশন বেছে নিন:", parse_mode="Markdown", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def check_bal(msg):
    b = get_bal(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💵 আপনার বর্তমান ব্যালেন্স: **${b:.2f}**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 My Profile")
def prof(msg):
    uid = msg.from_user.id
    b = get_bal(uid)
    bot.send_message(msg.chat.id, f"👤 **আপনার প্রোফাইল**\n\n🆔 User ID: `{uid}`\n💰 ব্যালেন্স: **${b:.2f}**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 Deposit")
def dep(msg):
    bot.send_message(msg.chat.id, f"💳 **ডিপোজিট করতে অ্যাডমিনের সাথে যোগাযোগ করুন**\n\nআপনার User ID (`{msg.from_user.id}`) অ্যাডমিনকে পাঠান।", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def with_start(msg):
    b = get_bal(msg.from_user.id)
    if b <= 0:
        bot.send_message(msg.chat.id, "❌ পর্যাপ্ত ব্যালেন্স নেই।")
        return
    m = bot.send_message(msg.chat.id, f"💸 ব্যালেন্স: **${b:.2f}**\n\nফরম্যাট: `Bkash | 01700000000 | 1.50`", parse_mode="Markdown")
    bot.register_next_step_handler(m, with_proc)

def with_proc(msg):
    try:
        uid = msg.from_user.id
        parts = [p.strip() for p in msg.text.split("|")]
        m, n, a = parts[0], parts[1], float(parts[2])
        if a <= 0 or a > get_bal(uid):
            bot.send_message(msg.chat.id, "❌ সঠিক পরিমাণ দিন।")
            return
        add_bal(uid, -a)
        bot.send_message(msg.chat.id, f"✅ আপনার **${a:.2f}** উইথড্র রিকোয়েস্ট পাঠানো হয়েছে।", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"🔔 **নতুন উইথড্র!**\n👤 `{uid}`\n💳 {m}: `{n}`\n💵 **${a:.2f}**", parse_mode="Markdown")
    except Exception:
        bot.send_message(msg.chat.id, "❌ ভুল ফরম্যাট!")

@bot.message_handler(func=lambda m: m.text == "📱 Buy Number")
def buy_menu(msg):
    if not db["services"]:
        bot.send_message(msg.chat.id, "❌ কোনো সার্ভিস অ্যাড করা নেই।")
        return
    markup = types.InlineKeyboardMarkup()
    for idx, srv in enumerate(db["services"]):
        markup.add(types.InlineKeyboardButton(f"{srv['name']} ({srv['country']}) - ${srv['price']:.2f}", callback_data=f"buy_{idx}"))
    bot.send_message(msg.chat.id, "🌍 নিচের তালিকা থেকে সার্ভিস সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_proc(c):
    idx = int(c.data.split("_")[1])
    uid = c.from_user.id
    if idx >= len(db["services"]):
        bot.answer_callback_query(c.id, "সার্ভিস পাওয়া যায়নি!")
        return
    srv = db["services"][idx]
    if get_bal(uid) < srv["price"]:
        bot.answer_callback_query(c.id, "❌ পর্যাপ্ত ব্যালেন্স নেই!", show_alert=True)
        return
    bot.edit_message_text("⏳ নাম্বার নেওয়া হচ্ছে...", c.message.chat.id, c.message.message_id)
    try:
        res = session.post(f"{BASE_URL}/getnum", headers=HEADERS, json={"rid": str(srv["rid"])}).json()
        if res.get("meta", {}).get("code") == 200 and res.get("data"):
            d = res["data"]
            add_bal(uid, -srv["price"])
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Check OTP", callback_data=f"otp_{d['no_plus_number']}"))
            bot.edit_message_text(f"✅ **নাম্বার কেনা হয়েছে!**\n\n📱 {srv['name']} ({srv['country']})\n📞 `{d['full_number']}`", c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.edit_message_text(f"❌ এরর: `{res.get('message', 'API Error')}`", c.message.chat.id, c.message.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ API এরর: `{e}`", c.message.chat.id, c.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("otp_"))
def otp_proc(c):
    num = c.data.split("_")[1]
    uid = c.from_user.id
    try:
        res = session.get(f"{BASE_URL}/success-otp", headers=HEADERS).json()
        for item in res.get("data", {}).get("otps", []):
            if str(item.get("number")) == str(num):
                rew = db.get("reward", 0.02)
                txt = ""
                if rew > 0:
                    add_bal(uid, rew)
                    txt = f"\n\n🎁 **বোনাস:** আপনার অ্যাকাউন্টে **${rew:.2f}** যোগ হয়েছে!"
                bot.edit_message_text(f"📩 **OTP কোড:** `{item.get('message')}`{txt}", c.message.chat.id, c.message.message_id, parse_mode="Markdown")
                return
        bot.answer_callback_query(c.id, "⏳ এখনো কোড আসেনি!", show_alert=True)
    except Exception:
        bot.answer_callback_query(c.id, "⚠️ চেক করতে সমস্যা হয়েছে!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.from_user.id == ADMIN_ID)
def adm_panel(msg):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Add Service", callback_data="adm_srv"), types.InlineKeyboardButton("💰 Add Balance", callback_data="adm_bal"))
    markup.add(types.InlineKeyboardButton("🎁 Set Reward", callback_data="adm_rew"))
    bot.send_message(msg.chat.id, "⚙️ **Admin Panel**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_") and c.from_user.id == ADMIN_ID)
def adm_act(c):
    act = c.data.split("_")[1]
    if act == "srv":
        m = bot.send_message(c.message.chat.id, "ফরম্যাট: `Telegram | UK | 26134 | 0`", parse_mode="Markdown")
        bot.register_next_step_handler(m, save_srv)
    elif act == "bal":
        m = bot.send_message(c.message.chat.id, "ফরম্যাট: `User_ID Amount` (যেমন: `7376984711 5`)", parse_mode="Markdown")
        bot.register_next_step_handler(m, save_bal)
    elif act == "rew":
        rew = db.get("reward", 0.02)
        m = bot.send_message(c.message.chat.id, f"বর্তমান বোনাস: **${rew:.2f}**\nনতুন বোনাস লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(m, save_rew)

def save_srv(msg):
    try:
        p = [x.strip() for x in msg.text.split("|")]
        db["services"].append({"name": p[0], "country": p[1], "rid": p[2], "price": float(p[3])})
        save_db()
        bot.send_message(msg.chat.id, f"✅ সার্ভিস **{p[0]} ({p[1]})** যুক্ত হয়েছে!", parse_mode="Markdown")
    except Exception:
        bot.send_message(msg.chat.id, "❌ ভুল ফরম্যাট!")

def save_bal(msg):
    try:
        u, a = msg.text.split()
        add_bal(int(u), float(a))
        bot.send_message(msg.chat.id, f"✅ ব্যালেন্স **${a}** যোগ হয়েছে!", parse_mode="Markdown")
    except Exception:
        bot.send_message(msg.chat.id, "❌ ভুল ফরম্যাট!")

def save_rew(msg):
    try:
        db["reward"] = float(msg.text.strip())
        save_db()
        bot.send_message(msg.chat.id, f"✅ বোনাস **${db['reward']:.2f}** সেট হয়েছে!", parse_mode="Markdown")
    except Exception:
        bot.send_message(msg.chat.id, "❌ সঠিক সংখ্যা দিন!")

print("Render Super Fast Bot is running...")
bot.infinity_polling(interval=0, timeout=15)
