"""
أدوات مساعدة عامة: حذف الملفات بأمان بعد الإرسال، وتنظيف دوري
لأي ملفات فضلت في مجلد downloads (بسبب كراش أو فشل إرسال مثلاً)،
وتصنيف أخطاء التحميل (محتوى خاص / rate-limit من المنصة نفسها / عادي).
"""
import os
import re
import time
import glob
import shutil
import uuid
from pathlib import Path

# مجلد التحميلات الأساسي - كل تحميل بياخد له مجلد فرعي فريد جواه
# (شوف new_download_dir) عشان منشاركش نفس الملفات بين تحميلات متزامنة
# من مستخدمين مختلفين (كان ده سبب باگ خطير: لو اتنين طلبوا نفس الفيديو
# في نفس الوقت كانوا بيكتبوا على نفس الملف، أو حذف تحميل واحد كان ممكن
# يمسح ملف تحميل تاني لسه شغال).
BASE_DOWNLOAD_DIR = "downloads"

# ✅ جديد: دعم الألبومات/الكاروسيل (بوست فيه أكتر من صورة/فيديو، زي
# كاروسيل إنستجرام) - حد أقصى لعدد العناصر في الألبوم الواحد عشان محدش
# يبعت لينك playlist ضخم (مثلاً) ويعمل ضغط على السيرفر أو يضرب حدود
# تيليجرام. إنستجرام نفسها بتحدد الكاروسيل بـ 10 عناصر، فالرقم ده أعلى
# من كفاية لأي منصة تانية بتدعم بوستات متعددة العناصر.
MAX_ALBUM_ITEMS = 20

# ✅ امتدادات الصور والفيديوهات اللي بنستخدمها لتصنيف عناصر الألبوم
# (نحدد الكابشن/النوع المناسب لكل عنصر لما نبعته بـ send_media_group)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".webm")


def classify_media_type(file_path: str) -> str:
    """يحدد نوع الملف (photo/video) من الامتداد - نستخدمها لعناصر الألبوم"""
    return "photo" if file_path.lower().endswith(IMAGE_EXTENSIONS) else "video"


def chunk_list(items, size=10):
    """
    يقسم لستة لمجموعات بحجم `size`. مستخدمة لما بنبعت ألبوم (كاروسيل)
    كـ media group في تيليجرام، لأن الحد الأقصى المسموح بيه لكل رسالة
    media group واحدة هو 10 عناصر بالظبط.
    """
    for i in range(0, len(items), size):
        yield items[i:i + size]

# رموز الـ Markdown اللي بايروجرام بيفسرها. لازم نهرّبها لما بنحقن نص
# جاي من مصدر خارجي (اسم مستخدم، عنوان فيديو، رسالة استثناء) جوه رسالة
# بنبعتها بـ parse_mode=MARKDOWN، وإلا تيليجرام هيرفض الرسالة بخطأ
# "Can't parse entities" أو التنسيق هيتلخبط.
_MD_SPECIAL_CHARS_RE = re.compile(r'([_*~`\[\]()])')


def escape_markdown(text: str) -> str:
    """يهرّب رموز الـ Markdown الخاصة في نص خارجي قبل حقنه في رسالة متنسقة"""
    if not text:
        return text
    return _MD_SPECIAL_CHARS_RE.sub(r'\\\1', text)


def new_download_dir(base: str = BASE_DOWNLOAD_DIR) -> str:
    """
    يجهّز مجلد فرعي فريد لكل عملية تحميل (باستخدام uuid) وينشئه لو لسه
    مش موجود. الهدف: عزل ملفات كل تحميل عن باقي التحميلات المتزامنة.
    """
    path = os.path.join(base, uuid.uuid4().hex)
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


class PrivateOrUnavailableError(Exception):
    """
    المحتوى خاص (Private) أو محتاج تسجيل دخول أو مش متاح من غير حساب،
    فمفيش داعي نحاول تاني - نبلّغ المستخدم على طول.
    """
    pass


class RateLimitedError(Exception):
    """
    المنصة نفسها (إنستجرام مثلاً) بترفض الطلبات مؤقتًا (rate limit من
    عندها، مش من عندنا) - الحل الوحيد إننا نستنى شوية ونجرب تاني.
    """
    pass


# ✅ إشارات نصية بنلاقيها في رسايل خطأ yt-dlp/instaloader بتدل إن
# المحتوى خاص/محتاج لوجين. لو حصل false-positive نادر مش مشكلة كبيرة
# لأن أسوأ حالة إن رسالة "خاص" تتبعت بدل رسالة الخطأ العامة.
_PRIVATE_MARKERS = (
    "empty media response",
    "logged-in",
    "logged in",
    "login required",
    "login page",
    "this account is private",
    "private account",
    "private but not followed",
    "the post may have been removed",
    "unable to extract shared data",
    "cookies-from-browser",
)

# ✅ إشارات إن المنصة بترفض الطلبات مؤقتًا (rate limit من عندها)
_RATE_LIMIT_MARKERS = (
    "please wait a few minutes",
    "rate-limit reached",
    "rate limit",
    "429",
    "too many requests",
)


def classify_download_error(message: str):
    """
    يفحص رسالة خطأ التحميل ويرجع:
    - "private"      لو المحتوى خاص/محتاج تسجيل دخول
    - "rate_limited"  لو المنصة نفسها بترفض الطلبات مؤقتًا
    - None            لو خطأ عادي/غير معروف (نسيبه يتعامل بالطريقة القديمة)
    """
    if not message:
        return None
    m = message.lower()

    if any(marker in m for marker in _RATE_LIMIT_MARKERS):
        return "rate_limited"

    if any(marker in m for marker in _PRIVATE_MARKERS):
        return "private"

    return None


def safe_delete_file(file_path: str):
    """احذف الملف بأمان - أي خطأ هنا متسيبوش يوقف تنفيذ البوت"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"[CLEANUP] 🗑️ Deleted: {file_path}")
    except Exception as e:
        print(f"[WARNING] Could not delete {file_path}: {str(e)[:80]}")


def safe_delete_download_dir(file_path: str, base: str = BASE_DOWNLOAD_DIR):
    """
    احذف مجلد التحميل الفريد بالكامل (مش الملف بس) - عشان نتخلص كمان من
    أي ملفات إضافية فضلت جواه (زي صور/metadata من instaloader). فيه تأكيد
    أمان إننا منمسحش غير مجلد فرعي جوه BASE_DOWNLOAD_DIR، مش المجلد
    الرئيسي نفسه ولا أي حاجة برّاه.
    """
    if not file_path:
        return
    try:
        directory = os.path.dirname(file_path) or "."
        base_abs = os.path.abspath(base)
        target_abs = os.path.abspath(directory)
        if target_abs == base_abs or not target_abs.startswith(base_abs + os.sep):
            # الملف مش جوه مجلد فرعي فريد (fallback قديم) - امسح الملف بس
            safe_delete_file(file_path)
            return
        shutil.rmtree(directory, ignore_errors=True)
        print(f"[CLEANUP] 🗑️ Removed download dir: {directory}")
    except Exception as e:
        print(f"[WARNING] Could not delete dir for {file_path}: {str(e)[:80]}")


def cleanup_stale_downloads(directory: str = "downloads", max_age_seconds: int = 3600):
    """
    يمسح أي ملفات قديمة فضلت في مجلد التحميلات (أقدم من max_age_seconds).
    مفيد لو حصل كراش أو فشل إرسال ومنفعش الملف يتمسح في وقته.
    """
    if not os.path.isdir(directory):
        return

    now = time.time()
    removed = 0

    for path in glob.glob(os.path.join(directory, "*")):
        try:
            age = now - os.path.getmtime(path)
            if age <= max_age_seconds:
                continue
            if os.path.isfile(path):
                os.remove(path)
                removed += 1
            elif os.path.isdir(path):
                # مجلد فرعي فريد قديم فضل من تحميل اتقفل من غير تنظيف
                # (كراش، فشل إرسال، إلخ) - نمسحه بالكامل
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except Exception as e:
            print(f"[WARNING] Cleanup failed for {path}: {str(e)[:60]}")

    if removed:
        print(f"[CLEANUP] 🧹 Removed {removed} stale item(s) from '{directory}/'")
