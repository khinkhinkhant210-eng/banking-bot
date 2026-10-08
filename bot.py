import logging
import os
from datetime import datetime
from threading import Thread
from flask import Flask

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

# User တစ်ဦးချင်းစီ၏ လက်ကျန်ငွေ
USER_BALANCES = {}

# User တစ်ဦးချင်းစီ၏ ငွေထုတ်ယူမှုမှတ်တမ်း
USER_HISTORY = {}

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


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history_list = USER_HISTORY .get(user_id,[])

    current_month = datetime.now().month
    current_year =datetime.now().year

    total_withdraw = 0.0
    total_deposited = 0.0
    withdraw_details = []

    for item in history _list:
        tx_date = datetime.strptime(item['date'],'%Y-%m-%d %H:%M')
        # လက်ရှိလအတွင်း ပြုလုပ်ခဲ့သော မှတ်တမ်းများကိုသာ စုပေါင်းခြင်း
        if tx_date.month == current_month and tx_date.year ==current_year:
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
    web_app.run(host="0.0.0.0",
    port=port)

Thread(target=run_web_server,
daemon=True).start()

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

    app.run_polling()


if __name__ == "__main__":
    main()
