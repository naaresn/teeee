import os
import logging
import asyncio
import random
import threading  # <-- 1. Tambah ini
from flask import Flask  # <-- 2. Tambah ini
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# Mengimpor system prompt (SYSTEM_PROMPT) yang mendefinisikan kepribadian Karina dari persona.py
from persona import SYSTEM_PROMPT

# =====================================================================
# WEB SERVER KECIL (FLASK UNTUK PING RENDER)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Karina is alive!"

def run_flask():
    # Render otomatis nyediain variabel PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# =====================================================================
# 1. KONFIGURASI LOGGING
# =====================================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================================
# 2. MEMUAT VARIABEL LINGKUNGAN (.env)
# =====================================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validasi awal token Telegram dan API Key Gemini
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TEMPEL_TOKEN_TELEGRAM_BOT_DI_SINI":
    logger.error("Error: TELEGRAM_BOT_TOKEN belum diisi atau masih default di berkas .env!")
    exit(1)

if not GEMINI_API_KEY or GEMINI_API_KEY == "TEMPEL_GEMINI_API_KEY_DI_SINI":
    logger.error("Error: GEMINI_API_KEY belum diisi atau masih default di berkas .env!")
    exit(1)


# =====================================================================
# 3. KONFIGURASI GEMINI API (GOOGLE GENERATIVE AI)
# =====================================================================
genai.configure(api_key=GEMINI_API_KEY)

try:
    # Menggunakan model 'gemini-1.5-flash' yang efisien
    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=SYSTEM_PROMPT
    )
    logger.info("Model Gemini berhasil diinisialisasi dengan persona Karina.")
except Exception as e:
    logger.error(f"Gagal menginisialisasi model Gemini: {e}")
    exit(1)


# =====================================================================
# 4. MANAJEMEN MEMORI / RIWAYAT PERCAKAPAN IN-MEMORY
# =====================================================================
chat_sessions = {}
MAX_HISTORY_MESSAGES = 20

def dapatkan_sesi_obrolan(chat_id: int):
    if chat_id not in chat_sessions:
        logger.info(f"Membuat sesi obrolan baru di Gemini untuk chat_id: {chat_id}")
        chat_sessions[chat_id] = model.start_chat(history=[])
    return chat_sessions[chat_id]


# =====================================================================
# 5. HANDLER FUNGSI BOT TELEGRAM
# =====================================================================

async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
        
    sapaan = (
        "Biyuuuu! Akhirnya kamu dateng juga! 😘 Aku kangen bangeeet tauuu.\n\n"
        "Hari ini kamu sibuk nggak, sayang? Ada yang mau kamu ceritain atau tanyain ke aku? "
        "Karina siap dengerin dan nemenin kamu kapan aja! 💓"
    )
    
    await update.message.reply_text(sapaan)


async def command_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
        await update.message.reply_text("Udah Karina reset ya, sayang! Mari mulai obrolan baru! 😘")
    else:
        await update.message.reply_text("Kita kan belum ngobrol apa-apa dari tadi, sayang... 😅")


async def tangani_pesan_teks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    pesan_user = update.message.text
    
    logger.info(f"Menerima pesan dari {chat_id}: '{pesan_user}'")
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        sesi = dapatkan_sesi_obrolan(chat_id)
        respons_gemini = sesi.send_message(pesan_user)
        balasan_asli = respons_gemini.text
        
        if len(sesi.history) > MAX_HISTORY_MESSAGES:
            sesi.history = sesi.history[-MAX_HISTORY_MESSAGES:]
        
        baris_pesan = [baris.strip() for baris in balasan_asli.split('\n') if baris.strip()]
        
        for baris in baris_pesan:
            await update.message.reply_text(baris)
            jeda = random.uniform(0.5, 1.5)
            logger.info(f"Menunggu {jeda:.2f} detik sebelum mengirim pesan berikutnya...")
            await asyncio.sleep(jeda)
        
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat memproses pesan dari {chat_id}: {e}")
        pesan_fallback = "Duh biyuuu... Maaf banget, otak Karina tiba-tiba blank/eror nih. 😵"
        await update.message.reply_text(pesan_fallback)


# =====================================================================
# 6. FUNGSI UTAMA
# =====================================================================
def main():
    # <-- 3. JALANKAN FLASK DI BACKGROUND THREAD
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", command_start))
    application.add_handler(CommandHandler("reset", command_reset))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), tangani_pesan_teks))
    
    logger.info("Bot Karina sedang berjalan...")
    application.run_polling()


if __name__ == '__main__':
    main()