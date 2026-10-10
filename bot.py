import logging
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# User တစ်ဦးချင်းစီ၏ စတင်သည့်ရက်ကို သိမ်းရန်
USER_START_DATES = {}


from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

DATA_FILE = "banking_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            balances = {int(k): v for k, v in data.get("balances", {}).items()}
            history = {int(k): v for k, v in data.get("history", {}).items()}
            return balances, history
    return {}, {}

def save_data():
    data = {
        "balances": USER_BALANCES,
        "history": USER_HISTORY
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ယာယီသိမ်းမည့်အစား ဖိုင်မှ ဒေတာများကို ဖတ်ယူမည်
USER_BALANCES, USER_HISTORY = load_data()

DEFAULT_BALANCE = 0.0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = DEFAULT_BALANCE

    await update.message.reply_text(
        "မင်္ဂလာပါ! Banking Assistant Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "• လက်ကျန်ငွေ စစ်ဆေးရန်: /balance\n"
        "• ငွေစာရင်းအသစ် သတ်မှတ်ရန်: /setbalance [ပမာဏ]\n"
        "• ငွေထုတ်ယူရန်: /withdraw [ပမာဏ] [အကြောင်းရင်း]\n"
        "• ငွေထည့်သွင်းရန်: /deposit [ပမာဏ]\n"
        "• ထုတ်ယူမှု မှတ်တမ်းကြည့်ရန်: /summary"
    )


async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        amount = float(context.args[0])

        if amount < 0:
            await update.message.reply_text(
                "ငွေပမာဏသည် 0 ထက်ငယ်၍ မရပါ။"
            )
            return

        USER_BALANCES[user_id] = amount
        save_data()

        await update.message.reply_text(
            f"သင့်၏ ငွေစာရင်းအသစ်ကို "
            f"{amount:,.2f} ကျပ် အဖြစ် သတ်မှတ်လိုက်ပါပြီ။"
        )

    except (IndexError, ValueError):
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ သတ်မှတ်လိုသော ပမာဏ ထည့်သွင်းပါ။\n"
            "ဥပမာ: /setbalance 5000000"
        )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    bal = USER_BALANCES.get(user_id, DEFAULT_BALANCE)

    await update.message.reply_text(
        f"💰 လက်ကျန်ငွေ စုစုပေါင်း: {bal:,.2f} ကျပ်"
    )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = DEFAULT_BALANCE

    if user_id not in USER_HISTORY:
        USER_HISTORY[user_id] = []

    try:
        amount = float(context.args[0])

        if amount <= 0:
            await update.message.reply_text(
                "ထုတ်ယူမည့် ပမာဏသည် 0 ထက်ကြီးရပါမည်။"
            )
            return

        # ကျန်တဲ့စာသားတွေကို Reason အဖြစ်ယူမည်
        reason = (
            " ".join(context.args[1:])
            if len(context.args) > 1
            else "အကြောင်းရင်း ဖော်ပြမထားပါ။"
        )

        # လက်ကျန်ငွေ စစ်ဆေးခြင်း
        if amount > USER_BALANCES[user_id]:
            await update.message.reply_text(
                "❌ လက်ကျန်ငွေ မလုံလောက်ပါ။"
            )
            return

        # ငွေထုတ်ခြင်း
        USER_BALANCES[user_id] -= amount

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # မှတ်တမ်းသိမ်းခြင်း
        USER_HISTORY[user_id].append({
            "amount": amount,
            "reason": reason,
            "date": current_time,
        })
        save_data()

        await update.message.reply_text(
            f"✅ {amount:,.2f} ကျပ် ထုတ်ယူလိုက်ပါပြီ။\n"
            f"📅 ရက်စွဲ: {current_time}\n"
            f"📝 အကြောင်းရင်း: {reason}\n"
            f"💰 ကျန်ရှိသော လက်ကျန်ငွေ: "
            f"{USER_BALANCES[user_id]:,.2f} ကျပ်"
        )

    except (IndexError, ValueError):
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ ပုံစံမှန်ကန်စွာ ထည့်သွင်းပါ။\n"
            "ဥပမာ: /withdraw 50000 စားစရာဝယ်ရန်"
        )


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = DEFAULT_BALANCE

    try:
        amount = float(context.args[0])

        if amount <= 0:
            await update.message.reply_text(
                "ထည့်သွင်းမည့် ပမာဏသည် 0 ထက်ကြီးရပါမည်။"
            )
            return

        USER_BALANCES[user_id] += amount
        save_data()

        await update.message.reply_text(
            f"✅ {amount:,.2f} ကျပ် ထည့်သွင်းလိုက်ပါပြီ။\n"
            f"💰 စုစုပေါင်း လက်ကျန်ငွေ: "
            f"{USER_BALANCES[user_id]:,.2f} ကျပ်"
        )

    except (IndexError, ValueError):
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ ပမာဏ ထည့်သွင်းပါ။\n"
            "ဥပမာ: /deposit 20000"
        )
async def check_monthly_reminders(application):
        now = datetime.now()
        for user_id, start_date in list(USER_START_DATES.items()):
        # တစ်လပြည့်ဖို့ ၁ ရက်အလို (၂၉ ရက်မြောက်နေ့) ရောက်ပြီလား စစ်ဆေးခြင်း
            if now - start_date >= timedelta(days=29) and now - start_date < timedelta(days=30):
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ **သတိပေးချက်**\n\nမနက်ဖြန်ဆိုရင် ဘတ်ဂျက်သတ်မှတ်ထားတဲ့ တစ်လပြည့်တော့မှာဖြစ်လို့ လက်ကျန်ငွေနဲ့ သုံးစွဲမှုမှတ်တမ်းတွေကို စစ်ဆေးပါ။",
            parse_mode="Markdown"
            )
                except Exception as e:
                    print(f"Error sending reminder to {user_id}: {e}")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history_list = USER_HISTORY.get(user_id, [])

    current_month = datetime.now().month
    current_year = datetime.now().year

    total_withdrawn = 0.0
    total_deposited = 0.0
    withdraw_details = []

    for item in history_list:
        tx_date = datetime.strptime(item['date'], '%Y-%m-%d %H:%M')
        if tx_date.month == current_month and tx_date.year == current_year:
            total_withdrawn += item['amount']
            withdraw_details.append(
                f"- {item['date']} - {item['amount']:,.2f} ကျပ် ({item['reason']})"
            )

    bal = USER_BALANCES.get(user_id, 0)

    summary_text = (
        f"📊 **Monthly Summary ({current_year}-{current_month:02d})**\n\n"
        f"💰 လက်ရှိ လက်ကျန်ငွေ: {bal:,.2f} ကျပ်\n"
        f"📤 ယခုလ စုစုပေါင်း ထုတ်ယူငွေ: {total_withdrawn:,.2f} ကျပ်\n\n"
        f"📝 **ထုတ်ယူမှု မှတ်တမ်းများ:**\n"
    )

    if withdraw_details:
        summary_text += "\n".join(withdraw_details)
    else:
        summary_text += "ယခုလအတွင်း ထုတ်ယူထားသော မှတ်တမ်း မရှိသေးပါ။"

    await update.message.reply_text(summary_text, parse_mode="Markdown")
    
#Flask web server
web_app = Flask(__name__)
@web_app.route("/")
def home():
    return "Bot is running!"
        
def run_web_server():
    port=int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0",port=port)
Thread(target=run_web_server, daemon=True).start()

def main():
    TOKEN ="8829496333:AAG3WdBg7nGv3jgqB2mcIVW9sqDa8ltpfCs"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler(["start","restart"], start))
    app.add_handler(CommandHandler("setbalance", set_balance))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("summary", summary))

    print("Bot အလုပ်စလုပ်နေပါပြီ...")
    
    # Scheduler စတင်ရန်
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_monthly_reminders, "cron", hour=9, minute=0, args=[app])
    scheduler.start()


    app.run_polling()


if __name__ == "__main__":
    main()
