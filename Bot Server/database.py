"""
قاعدة بيانات بسيطة بـ SQLite لتخزين:
1. سجل التحميلات (للإحصائيات)
2. المستخدمين (تاريخ أول/آخر ظهور + عدد التحميلات)
3. حد الاستخدام (Rate Limiting) - نافذة زمنية متجددة لكل مستخدم
"""
import sqlite3
import time
import threading
from typing import Tuple

DB_PATH = "bot_data.db"
_lock = threading.Lock()

# ─── إعدادات حد الاستخدام ───────────────────────────────
RATE_LIMIT_MAX = 10        # أقصى عدد تحميلات
RATE_LIMIT_WINDOW = 3600   # خلال ساعة (بالثواني)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """ينشئ الجداول لو مش موجودة - ينادى مرة واحدة عند تشغيل البوت"""
    with _lock:
        conn = _get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                platform TEXT,
                media_type TEXT,
                url TEXT,
                file_size_mb REAL,
                created_at INTEGER,
                album_id TEXT,
                album_total INTEGER
            )
        """)
        # ✅ لو قاعدة البيانات كانت موجودة من قبل إضافة دعم الألبومات
        # (يعني جدول downloads كان موجود بالفعل من غير العمودين الجداد)،
        # CREATE TABLE IF NOT EXISTS مش بيعدّل جدول موجود، فلازم نضيف
        # العمودين يدويًا. try/except عشان الكود يفضل idempotent لو
        # العمود موجود بالفعل (قاعدة بيانات جديدة أصلًا).
        for col_def in ("album_id TEXT", "album_total INTEGER"):
            try:
                conn.execute(f"ALTER TABLE downloads ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                first_seen INTEGER,
                last_seen INTEGER,
                total_downloads INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                chat_id INTEGER PRIMARY KEY,
                window_start INTEGER,
                count INTEGER
            )
        """)
        conn.commit()
        conn.close()
    print("[DATABASE] ✅ Initialized successfully")


def touch_user(chat_id: int):
    """يسجل/يحدّث ظهور المستخدم (بينادى مثلاً عند /start)"""
    now = int(time.time())
    with _lock:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO users (chat_id, first_seen, last_seen, total_downloads) "
            "VALUES (?, ?, ?, 0) "
            "ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen",
            (chat_id, now, now)
        )
        conn.commit()
        conn.close()


def log_download(chat_id: int, platform: str, media_type: str, url: str, file_size_mb: float,
                  album_id: str = None, album_total: int = None):
    """
    يسجل عملية تحميل ناجحة في قاعدة البيانات. album_id/album_total
    اختياريين - بيتحطوا لما التحميل ده عنصر من ألبوم/كاروسيل (كل عناصر
    نفس الألبوم بتاخد نفس الـ album_id)، وبيفضلوا None لتحميل عادي
    (نفس السلوك القديم بالظبط لو محدش استخدم الباراميترين الجداد).
    """
    now = int(time.time())
    with _lock:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO downloads (chat_id, platform, media_type, url, file_size_mb, created_at, album_id, album_total) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, platform, media_type, url, file_size_mb, now, album_id, album_total)
        )
        conn.execute(
            "INSERT INTO users (chat_id, first_seen, last_seen, total_downloads) "
            "VALUES (?, ?, ?, 1) "
            "ON CONFLICT(chat_id) DO UPDATE SET "
            "last_seen = excluded.last_seen, total_downloads = total_downloads + 1",
            (chat_id, now, now)
        )
        conn.commit()
        conn.close()


def get_global_stats() -> dict:
    """إحصائيات عامة عن كل البوت"""
    with _lock:
        conn = _get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM downloads")
        total_downloads = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute(
            "SELECT platform, COUNT(*) c FROM downloads GROUP BY platform ORDER BY c DESC"
        )
        by_platform = cur.fetchall()

        cur.execute("SELECT COALESCE(SUM(file_size_mb), 0) FROM downloads")
        total_mb = cur.fetchone()[0]

        # ✅ جديد: إحصائيات الألبومات (بوستات فيها أكتر من صورة/فيديو
        # اتحملت مرة واحدة من نفس اللينك)
        cur.execute("SELECT COUNT(DISTINCT album_id) FROM downloads WHERE album_id IS NOT NULL")
        total_albums = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM downloads WHERE album_id IS NOT NULL")
        total_album_items = cur.fetchone()[0]

        conn.close()

    return {
        "total_downloads": total_downloads,
        "total_users": total_users,
        "by_platform": by_platform,
        "total_mb": total_mb,
        "total_albums": total_albums,
        "total_album_items": total_album_items,
    }


def get_user_stats(chat_id: int) -> dict:
    """إحصائيات مستخدم معيّن"""
    with _lock:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT total_downloads, first_seen FROM users WHERE chat_id = ?",
            (chat_id,)
        )
        row = cur.fetchone()
        conn.close()

    if row:
        return {"total_downloads": row[0], "first_seen": row[1]}
    return {"total_downloads": 0, "first_seen": None}


def check_rate_limit(chat_id: int) -> Tuple[bool, int, int]:
    """
    يتحقق من حد الاستخدام لمستخدم معيّن.
    Returns: (allowed, remaining, reset_in_seconds)
    """
    now = int(time.time())
    with _lock:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT window_start, count FROM rate_limits WHERE chat_id = ?",
            (chat_id,)
        )
        row = cur.fetchone()

        # مفيش سجل أو النافذة الزمنية انتهت -> نافذة جديدة
        if row is None or (now - row[0]) >= RATE_LIMIT_WINDOW:
            conn.execute(
                "INSERT INTO rate_limits (chat_id, window_start, count) VALUES (?, ?, 1) "
                "ON CONFLICT(chat_id) DO UPDATE SET window_start = excluded.window_start, count = 1",
                (chat_id, now)
            )
            conn.commit()
            conn.close()
            return True, RATE_LIMIT_MAX - 1, RATE_LIMIT_WINDOW

        window_start, count = row

        if count >= RATE_LIMIT_MAX:
            conn.close()
            reset_in = max(RATE_LIMIT_WINDOW - (now - window_start), 0)
            return False, 0, reset_in

        conn.execute(
            "UPDATE rate_limits SET count = count + 1 WHERE chat_id = ?",
            (chat_id,)
        )
        conn.commit()
        conn.close()
        reset_in = max(RATE_LIMIT_WINDOW - (now - window_start), 0)
        return True, RATE_LIMIT_MAX - count - 1, reset_in
