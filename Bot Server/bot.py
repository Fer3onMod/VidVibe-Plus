#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import threading
import asyncio

# ─── Auto-update pip & yt-dlp before anything else ────────
def auto_update():
    updates = [
        ([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "-q"], "pip"),
        ([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "-q"], "yt-dlp"),
    ]
    for cmd, name in updates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[UPDATE] ✅ {name} updated successfully")
            else:
                print(f"[UPDATE] ⚠️  {name} update failed — continuing anyway")
        except Exception as e:
            print(f"[UPDATE] ⚠️  {name} error: {str(e)[:60]} — continuing anyway")

auto_update()
# ───────────────────────────────────────────────────────────

# ✅ حل مشكلة التوافق مع بايثون 3.14 و Pyrogram
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, enums
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import setup_handlers
from database import init_db
from utils import cleanup_stale_downloads
from api import start_api_server_background

print("\n" + "=" * 60)
print("🚀 VIDEO DOWNLOADER BOT & API v2026")
print("=" * 60)
print("[INIT] Initializing bot & API...\n")

# تهيئة قاعدة البيانات
init_db()

# تنظيف دوري للملفات
def _schedule_cleanup():
    cleanup_stale_downloads()
    timer = threading.Timer(3600, _schedule_cleanup)
    timer.daemon = True
    timer.start()

_schedule_cleanup()

# ✅ تشغيل سيرفر الـ API لتطبيق الأندرويد في الخلفية
start_api_server_background()

# ✅ إعداد بوت التيليجرام
app = Client(
    "VideoDownloaderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.DISABLED
)

setup_handlers(app)

print("[INIT] Bot initialized successfully!")
print("=" * 60)
print("[START] Bot is now running on Telegram...\n")

# تشغيل البوت
app.run()
