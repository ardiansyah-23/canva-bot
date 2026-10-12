import os
import re
import asyncio
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SESSION_FILE = "canva_session.json"

queue = asyncio.Queue()

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

async def invite_canva(email: str) -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        try:
            context = await browser.new_context(storage_state=SESSION_FILE)
            page = await context.new_page()

            # Buka halaman member
            await page.goto("https://www.canva.com/settings/your-team/members", timeout=60000)

            # Klik tombol invite
            await page.click("button:has-text('Invite people'), button:has-text('Undang orang')")
            
            # Input email
            email_input = page.locator("input[type='email'], input[placeholder*='name@example.com']")
            await email_input.fill(email)
            await page.keyboard.press("Enter")

            # Kirim invite
            await page.click("button:has-text('Send invitations'), button:has-text('Kirim undangan')")
            await page.wait_for_timeout(3000)

            await browser.close()
            return True
        except Exception as e:
            print(f"[ERROR] Gagal invite {email}: {e}")
            await browser.close()
            return False

async def worker():
    """Memproses invite satu per satu dari antrean."""
    while True:
        update, email = await queue.get()
        try:
            await update.message.reply_text(f"Sedang memproses invite untuk {email}...")
            success = await invite_canva(email)
            if success:
                await update.message.reply_text(f"Berhasil! Undangan telah dikirim ke {email}.")
            else:
                await update.message.reply_text(f"Gagal mengundang {email}. Silakan hubungi admin.")
        finally:
            queue.task_done()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not is_valid_email(text):
        await update.message.reply_text("Format email tidak valid. Masukkan email yang benar.")
        return

    await update.message.reply_text(f"Email {text} diterima dan masuk antrean...")
    await queue.put((update, text))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan email Canva kamu untuk mendapatkan invite ke tim.")

async def post_init(application):
    asyncio.create_task(worker())

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot berjalan...")
    app.run_polling()
