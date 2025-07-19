# --- SOL TRACKER BOT --- #

import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime
import os
from flask import Flask
import threading

# === Bot Token ===
BOT_TOKEN = "7903534242:AAHOGE3qF3xpevpMgcD4P-dYsmTnhFvz6JA"  # Replace with your bot token

# === Solana RPC ===
RPC = "https://api.mainnet-beta.solana.com"
WALLET_FILE = "wallets.json"

# === Flask server to keep alive ===
web = Flask('')

@web.route('/')
def home():
    return "I'm alive!"

def run():
    web.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# === Load wallets ===
if os.path.exists(WALLET_FILE):
    with open(WALLET_FILE, "r") as f:
        user_wallets = json.load(f)
else:
    user_wallets = {}

def save_wallets():
    with open(WALLET_FILE, "w") as f:
        json.dump(user_wallets, f)

def get_wallet(user_id):
    return user_wallets.get(str(user_id), None)

# === COMMANDS === #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 Solana Tracker Bot\n\n"
        "Use these:\n"
        "/setwallet <your_address>\n"
        "/solbalance – Check SOL\n"
        "/solairdrops – Tokens\n"
        "/sollog – Transactions"
    )

async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 1:
            await update.message.reply_text("❌ Usage: /setwallet <your_solana_wallet>")
            return
        wallet = context.args[0]
        user_id = update.effective_user.id
        user_wallets[str(user_id)] = wallet
        save_wallets()
        await update.message.reply_text(f"✅ Wallet saved: `{wallet}`", parse_mode="Markdown")
    except Exception as e:
        print("Error in /setwallet:", e)
        await update.message.reply_text("⚠️ Something went wrong.")

async def solbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = get_wallet(user_id)
    if not wallet:
        await update.message.reply_text("⚠️ Use /setwallet first.")
        return

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet]
    }
    res = requests.post(RPC, json=payload).json()
    lamports = res.get("result", {}).get("value", 0)
    sol = lamports / 1_000_000_000
    await update.message.reply_text(
        f"📟 Wallet: `{wallet}`\n💰 Balance: {sol:.4f} SOL",
        parse_mode="Markdown"
    )

async def solairdrops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = get_wallet(user_id)
    if not wallet:
        await update.message.reply_text("⚠️ Use /setwallet first.")
        return

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ]
    }
    res = requests.post(RPC, json=payload).json()
    accounts = res.get("result", {}).get("value", [])
    tokens = []
    for acc in accounts:
        info = acc["account"]["data"]["parsed"]["info"]
        mint = info.get("mint", "")[-4:]
        amount = float(info["tokenAmount"]["uiAmountString"])
        if amount > 0:
            tokens.append(f"- {amount:.4f} [{mint}]")
    if not tokens:
        await update.message.reply_text("📭 No airdropped tokens found.")
    else:
        await update.message.reply_text("🎁 Airdropped Tokens:\n" + "\n".join(tokens))

async def sollog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = get_wallet(user_id)
    if not wallet:
        await update.message.reply_text("⚠️ Use /setwallet first.")
        return

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet, {"limit": 5}]
    }
    res = requests.post(RPC, json=payload).json()
    txs = res.get("result", [])
    if not txs:
        await update.message.reply_text("📭 No recent transactions found.")
        return

    log = "🧾 Last 5 Transactions:\n"
    for tx in txs:
        sig = tx.get("signature", "")[:8]
        time_unix = tx.get("blockTime", 0)
        dt = datetime.utcfromtimestamp(time_unix).strftime('%Y-%m-%d %H:%M')
        status = "✅" if tx.get("err") is None else "❌"
        log += f"{status} {dt} — `{sig}...`\n"

    await update.message.reply_text(log, parse_mode="Markdown")

# === MAIN RUN === #

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setwallet", setwallet))
app.add_handler(CommandHandler("solbalance", solbalance))
app.add_handler(CommandHandler("solairdrops", solairdrops))
app.add_handler(CommandHandler("sollog", sollog))

keep_alive()  # Keeps it alive for UptimeRobot/cron
app.run_polling()
  
