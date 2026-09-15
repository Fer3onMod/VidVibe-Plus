import yt_dlp
import os
import glob
from pathlib import Path
from typing import Optional
from utils import PrivateOrUnavailableError, RateLimitedError, classify_download_error, new_download_dir, MAX_ALBUM_ITEMS


class ModernVideoDownloader:
    """Universal video downloader for multiple platforms"""

    def __init__(self, output_dir: Optional[str] = None):
        # ✅ باگ كان موجود: كل التحميلات كانت بتشترك في نفس مجلد "downloads"
        # وبتسمي الملف بـ video id بس - لو اتنين مستخدمين طلبوا نفس الفيديو
        # في نفس الوقت (asyncio.to_thread بيشغلهم فعليًا بالتوازي) كانوا
        # بيكتبوا على نفس الملف، وحذف تحميل واحد بعد الإرسال كان ممكن يمسح
        # ملف التحميل التاني وهو لسه بيترفع. دلوقتي كل instance بياخد مجلد
        # فرعي فريد (uuid) خاص بيه بس، ومنعملش mkdir غير وقت التحميل الفعلي
        # (مش في get_available_formats اللي مش محتاجة تكتب أي ملف أصلاً).
        self.output_dir = output_dir  # None لحد ما يتحدد وقت أول تحميل فعلي
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
        # ✅ بنسجل هنا آخر رسالة خطأ حصلت في get_available_formats، عشان
        # اللي بينادي الدالة يقدر يميّز بين "مفيش جودات متعددة عادي" و
        # "المنصة رافضة الطلب / محتاجة لوجين / عاملة rate limit" - الحالة
        # التانية دي لازم توقف على طول من غير ما تحاول تاني بطريقة تانية.
        self.last_error = None

    def _ensure_output_directory(self) -> str:
        """يجهّز مجلد فريد لهذا التحميل لو مفيش واحد متحدد لحد دلوقتي، وينشئه"""
        if not self.output_dir:
            self.output_dir = new_download_dir()
        else:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def detect_platform(self, url: str) -> str:
        url_lower = url.lower()
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'YouTube Shorts' if '/shorts/' in url_lower else 'YouTube'
        elif 'tiktok.com' in url_lower:
            return 'TikTok'
        elif 'instagram.com' in url_lower:
            return 'Instagram'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'Twitter/X'
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
            return 'Facebook'
        elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
            # pin.it هو الدومين المختصر (short link) اللي بينتريست بيستخدمه
            return 'Pinterest'
        else:
            return 'Unknown'

    def _get_ydl_opts(self, attempt: int = 1) -> dict:
        """
        3 محاولات بـ player_client مختلف —
        android اتشال لأنه بيعمل HTTP 400 مع YouTube.
        """
        base = {
            # ✅ نستخدم video ID في الاسم عشان نقدر نلاقي الملف بسهولة
            'outtmpl': os.path.join(self.output_dir, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 40,
            'retries': 3,
            'fragment_retries': 3,
            'http_headers': {'User-Agent': self.user_agent},
        }

        if attempt == 1:
            base.update({
                'format': 'best[ext=mp4]/best',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios', 'web'],
                        'player_skip': ['webpage', 'configs'],
                    }
                },
            })
        elif attempt == 2:
            base.update({
                'format': 'best[ext=mp4]/best',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv_embedded', 'mweb'],
                    }
                },
            })
        else:
            base.update({'format': 'best'})

        return base

    def _make_progress_hook(self, progress_callback):
        """
        يحوّل تحديثات yt-dlp الخام (progress_hooks) لشكل بسيط
        {status, percent, downloaded_mb, total_mb, speed} عشان نستخدمه في شريط تقدم حقيقي
        """
        def hook(d):
            if not progress_callback:
                return
            try:
                if d.get('status') == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    percent = (downloaded / total * 100) if total else 0
                    progress_callback({
                        'status': 'downloading',
                        'percent': percent,
                        'downloaded_mb': downloaded / (1024 * 1024),
                        'total_mb': total / (1024 * 1024) if total else 0,
                        'speed': d.get('speed') or 0,
                    })
                elif d.get('status') == 'finished':
                    progress_callback({'status': 'finished', 'percent': 100})
            except Exception:
                pass
        return hook

    def _find_downloaded_file(self, video_id: str) -> Optional[str]:
        """ابحث عن الملف بالـ video ID لو الاسم اختلف بعد المعالجة (مثلاً بعد merge)"""
        for pattern in [
            os.path.join(self.output_dir, f"{video_id}.*"),
            os.path.join(self.output_dir, f"*{video_id}*"),
        ]:
            files = glob.glob(pattern)
            if files:
                # فضّل أحدث ملف (بعد الـ merge بيكون أحدث من الأجزاء)
                files.sort(key=os.path.getmtime, reverse=True)
                return files[0]
        return None

    # ─────────────────────────────────────────────────────────
    # ✅ جديد: اكتشاف الجودات المتاحة من غير تحميل
    # ─────────────────────────────────────────────────────────
    def get_available_formats(self, url: str) -> Optional[dict]:
        """
        يجيب الجودات المتاحة للفيديو (من الأقل للأعلى) من غير أي تحميل فعلي.
        Returns: {title, duration, platform, qualities: [{height, format_id, ext, filesize, has_audio}]}
        أو None لو فشل الاستخراج (مثلاً منصات زي Instagram الخاصة أو روابط غير مدعومة).
        """
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'socket_timeout': 30,
            'http_headers': {'User-Agent': self.user_agent},
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'web']}
            },
        }

        self.last_error = None

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # ✅ جديد: لو اللينك ده لبوست/صفحة فيها أكتر من عنصر (playlist
            # من وجهة نظر yt-dlp - زي تغريدة فيها أكتر من صورة/فيديو،
            # ألبوم فيسبوك، بورد بينتريست...)، منعملش قائمة جودات عادية،
            # وبدل كده نبلّغ اللي بينادي الدالة إن ده "ألبوم" عشان يستخدم
            # مسار تحميل الألبوم (multi_platform.download_generic_album)
            # بدل مسار الفيديو الواحد.
            entries = list(info.get('entries') or [])
            if len(entries) > 1:
                return {
                    'title': info.get('title', 'album'),
                    'platform': self.detect_platform(url),
                    'is_album': True,
                    'album_count': min(len(entries), MAX_ALBUM_ITEMS),
                    'qualities': [],
                }

            formats = info.get('formats', []) or []
            best_by_height = {}

            for f in formats:
                height = f.get('height')
                vcodec = f.get('vcodec', 'none')
                if not height or vcodec == 'none':
                    continue

                filesize = f.get('filesize') or f.get('filesize_approx') or 0

                # نحتفظ بأفضل نسخة (أكبر حجم) لكل ارتفاع (height) عشان منكررش نفس الجودة
                if height not in best_by_height or filesize > best_by_height[height]['filesize']:
                    best_by_height[height] = {
                        'height': height,
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext', 'mp4'),
                        'filesize': filesize,
                        'has_audio': f.get('acodec', 'none') != 'none',
                    }

            qualities = sorted(best_by_height.values(), key=lambda x: x['height'])

            if not qualities:
                return None

            return {
                'title': info.get('title', 'video'),
                'duration': info.get('duration', 0) or 0,
                'platform': self.detect_platform(url),
                'qualities': qualities,
            }

        except Exception as e:
            err = str(e)
            self.last_error = err
            kind = classify_download_error(err)
            if kind == "private":
                raise PrivateOrUnavailableError(err) from e
            if kind == "rate_limited":
                raise RateLimitedError(err) from e
            print(f"[WARNING] Could not fetch formats: {err[:120]}")
            return None

    # ─────────────────────────────────────────────────────────
    # ✅ جديد: تحميل بجودة محددة (مع دمج الصوت لو الفورمات صامت)
    # ─────────────────────────────────────────────────────────
    def download_with_format(self, url: str, quality: dict, progress_callback=None) -> Optional[str]:
        """تحميل الفيديو بالجودة اللي المستخدم اختارها"""
        self._ensure_output_directory()
        format_id = quality.get('format_id')
        # لو الفورمات ده فيديو بس من غير صوت (شائع في جودات الـ DASH العالية) هندمج معاه bestaudio
        fmt_string = format_id if quality.get('has_audio') else f"{format_id}+bestaudio/best"

        opts = {
            'outtmpl': os.path.join(self.output_dir, '%(id)s.%(ext)s'),
            'format': fmt_string,
            'merge_output_format': 'mp4',
            'quiet': False,
            'socket_timeout': 60,
            'retries': 3,
            'fragment_retries': 3,
            'http_headers': {'User-Agent': self.user_agent},
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'web']}
            },
            'progress_hooks': [self._make_progress_hook(progress_callback)],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                print(f"[YT-DLP] Downloading format {fmt_string}...")
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id', '')
                file_path = ydl.prepare_filename(info)

                # بعد الـ merge بيتغير الامتداد لـ mp4
                if not os.path.exists(file_path):
                    base, _ = os.path.splitext(file_path)
                    candidate = base + '.mp4'
                    if os.path.exists(candidate):
                        file_path = candidate

                if not os.path.exists(file_path):
                    file_path = self._find_downloaded_file(video_id)

                if file_path and os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"[DOWNLOAD_SUCCESS] {size_mb:.2f} MB @ {quality.get('height')}p")
                    return file_path

                print("[ERROR] File not found after download")
                return None

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Format download failed: {err_msg[:120]}")
            return None

    # ─────────────────────────────────────────────────────────
    # ✅ جديد: تحميل الصوت فقط (MP3) - لازم ffmpeg متثبت على السيرفر
    # ─────────────────────────────────────────────────────────
    def download_audio_only(self, url: str, progress_callback=None) -> Optional[str]:
        """تحميل الصوت فقط من أي فيديو وتحويله لـ MP3"""
        self._ensure_output_directory()
        opts = {
            'outtmpl': os.path.join(self.output_dir, '%(id)s.%(ext)s'),
            'format': 'bestaudio/best',
            'quiet': False,
            'socket_timeout': 60,
            'retries': 3,
            'http_headers': {'User-Agent': self.user_agent},
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'extractor_args': {
                'youtube': {'player_client': ['ios', 'web']}
            },
            'progress_hooks': [self._make_progress_hook(progress_callback)],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                print("[YT-DLP] Extracting audio...")
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id', '')
                file_path = os.path.join(self.output_dir, f"{video_id}.mp3")

                if not os.path.exists(file_path):
                    file_path = self._find_downloaded_file(video_id)

                if file_path and os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"[AUDIO_SUCCESS] {size_mb:.2f} MB")
                    return file_path

                print("[ERROR] Audio file not found after extraction")
                return None

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Audio download failed: {err_msg[:120]}")
            return None

    def download(self, url: str, progress_callback=None) -> Optional[str]:
        """Download with automatic fallback across 3 attempts (أفضل جودة تلقائيًا)"""
        self._ensure_output_directory()
        platform = self.detect_platform(url)
        print(f"[PLATFORM_DETECT] {platform}")

        for attempt in range(1, 4):
            print(f"[DOWNLOAD_ATTEMPT] #{attempt} — {platform}")
            opts = self._get_ydl_opts(attempt)
            opts['progress_hooks'] = [self._make_progress_hook(progress_callback)]

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_id = info.get('id', '')
                    file_path = ydl.prepare_filename(info)

                    if not os.path.exists(file_path):
                        file_path = self._find_downloaded_file(video_id)

                    if file_path and os.path.exists(file_path):
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"[DOWNLOAD_SUCCESS] {platform}: {size_mb:.2f} MB")
                        return file_path

                    print(f"[WARNING] Attempt #{attempt}: file not found after download")

            except Exception as e:
                err_msg = str(e)
                kind = classify_download_error(err_msg)
                if kind == "private":
                    raise PrivateOrUnavailableError(err_msg) from e
                if kind == "rate_limited":
                    raise RateLimitedError(err_msg) from e

                print(f"[WARNING] Attempt #{attempt} failed: {err_msg[:120]}")
                if attempt == 3:
                    print("[ERROR] All 3 attempts failed — giving up")
                    return None

        return None


# ─── Wrappers للاستخدام المباشر من handlers.py ──────────────
def download_youtube_video(
    url: str,
    client=None,
    chat_id: Optional[int] = None,
    download_type: str = "video",
    progress_callback=None
) -> Optional[str]:
    downloader = ModernVideoDownloader()
    return downloader.download(url, progress_callback)


def get_video_formats(url: str) -> "tuple[Optional[dict], Optional[str]]":
    """
    يجيب الجودات المتاحة للرابط (بدون تحميل).
    Returns: (info_or_None, error_message_or_None)
    """
    downloader = ModernVideoDownloader()
    info = downloader.get_available_formats(url)
    return info, downloader.last_error


# ✅ عبارات بتدل إن المنصة (غالبًا Instagram) رافضة الطلب فعليًا -
# محتاجة لوجين أو عاملة rate limit - مش مجرد "مفيش جودات متعددة".
# في الحالة دي مفيش فايدة إننا نحاول تاني بطريقة تانية فورًا؛ ده هيزود
# احتمال الحظر بدل ما يحله.
_BLOCKING_ERROR_MARKERS = (
    "empty media response",
    "rate limit",
    "please wait a few minutes",
    "429",
    " 401 ",
    " 403 ",
    "login required",
    "requested content is not available",
    "restricted video",
)


def is_platform_blocking_error(error_message: Optional[str]) -> bool:
    """يتحقق هل رسالة الخطأ بتدل على إن المنصة رافضة/حاظرة الطلب"""
    if not error_message:
        return False
    text = error_message.lower()
    return any(marker in text for marker in _BLOCKING_ERROR_MARKERS)


def download_video_with_quality(url: str, quality: dict, progress_callback=None) -> Optional[str]:
    """يحمل الفيديو بجودة محددة اختارها المستخدم"""
    downloader = ModernVideoDownloader()
    return downloader.download_with_format(url, quality, progress_callback)


def download_audio(url: str, progress_callback=None) -> Optional[str]:
    """يحمل الصوت فقط (MP3)"""
    downloader = ModernVideoDownloader()
    return downloader.download_audio_only(url, progress_callback)


def detect_platform(url: str) -> str:
    """دالة مستقلة لاكتشاف المنصة - تستخدم في الإحصائيات وغيرها"""
    return ModernVideoDownloader().detect_platform(url)
