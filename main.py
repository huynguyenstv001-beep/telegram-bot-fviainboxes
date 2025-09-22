import asyncio
import re
import requests
import random
import string
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_BASE = "https://inboxes.com"   # ⚠️ đổi đúng endpoint fviainboxes.com
API_KEY = None
TELEGRAM_TOKEN = "8311032731:AAExXQI_ntr-TKjkJ9DIii9vi7DPMKDwkMI"

HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

# Lưu inbox cuối cùng của từng user
user_last_inbox = {}

# --- TẠO CHUỖI RANDOM (cho email mới) ---
def random_inbox(length=10):
    letters = string.ascii_lowercase + string.digits
    return "".join(random.choice(letters) for _ in range(length))

# --- HÀM LẤY MAIL THÔ ---
def fetch_inbox(inbox: str):
    try:
        requests.post(f"{API_BASE}/inboxes/{inbox}", headers=HEADERS, timeout=10)
        r = requests.get(f"{API_BASE}/inboxes/{inbox}/messages", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []
        return r.json()
    except Exception:
        return []

# --- HÀM XỬ LÝ MAIL ---
def extract_otps(messages: list):
    result = []
    otp_regex = re.compile(r"\b\d{6}\b")
    for msg in messages[:5]:
        body = msg.get("body") or msg.get("excerpt") or ""
        otp_match = otp_regex.search(body)
        if otp_match:
            result.append(otp_match.group(0))
    return result

def process_messages(messages: list):
    result = []
    otp_regex = re.compile(r"\b\d{6}\b")
    for msg in messages[:5]:
        frm = msg.get("from") or "Unknown"
        subj = msg.get("subject") or "(no subject)"
        body = msg.get("body") or msg.get("excerpt") or ""
        otp_match = otp_regex.search(body)
        if otp_match:
            otp = otp_match.group(0)
            result.append(f"✅ OTP từ {frm}\n📌 Subject: {subj}\n🔑 Mã: {otp}")
        else:
            body_cut = body[:200]
            result.append(f"📧 From: {frm}\n📝 Subject: {subj}\n{body_cut}")
    return result

# --- HANDLERS TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Lệnh có sẵn:\n"
        "/new → tạo email mới\n"
        "/get → lấy mail từ inbox vừa tạo/gần nhất\n"
        "/get <inbox> → lấy mail của inbox chỉ định\n"
        "/otp → lấy OTP từ inbox gần nhất\n"
        "/otp <inbox> → lấy OTP từ inbox chỉ định"
    )

async def new_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inbox = random_inbox()
    try:
        email = f"{inbox}@fviainboxes.com"
        user_last_inbox[update.effective_user.id] = inbox  # lưu luôn
        await update.message.reply_text(f"✅ Đã tạo email mới:\n`{email}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Lỗi khi tạo inbox: {e}")

async def get_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Nếu có tham số → dùng inbox đó
    if context.args:
        inbox = context.args[0]
        user_last_inbox[user_id] = inbox
    else:
        inbox = user_last_inbox.get(user_id)

    if not inbox:
        await update.message.reply_text("❌ Chưa có inbox nào. Hãy dùng `/new` hoặc `/get <inbox>` trước.")
        return

    await update.message.reply_text(f"📨 Đang lấy mail cho: {inbox} ...")

    raw_messages = fetch_inbox(inbox)
    if not raw_messages:
        await update.message.reply_text("❌ Không có thư hoặc lỗi khi lấy inbox.")
        return

    processed = process_messages(raw_messages)
    for text in processed:
        await update.message.reply_text(text)

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args:
        inbox = context.args[0]
        user_last_inbox[user_id] = inbox
    else:
        inbox = user_last_inbox.get(user_id)

    if not inbox:
        await update.message.reply_text("❌ Chưa có inbox nào. Hãy dùng `/new` hoặc `/get <inbox>` trước.")
        return

    await update.message.reply_text(f"🔍 Đang lấy OTP từ inbox: {inbox} ...")

    raw_messages = fetch_inbox(inbox)
    if not raw_messages:
        await update.message.reply_text("❌ Không có thư hoặc lỗi khi lấy inbox.")
        return

    otps = extract_otps(raw_messages)
    if not otps:
        await update.message.reply_text("📭 Không tìm thấy OTP trong thư mới nhất.")
        return

    for otp in otps:
        await update.message.reply_text(f"🔑 OTP: {otp}")

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_inbox))
    app.add_handler(CommandHandler("get", get_inbox))
    app.add_handler(CommandHandler("otp", get_otp))
    print("Bot started (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
