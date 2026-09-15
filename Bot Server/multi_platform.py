import yt_dlp
import instaloader
import os
import glob
from pathlib import Path
from typing import Optional
from utils import (
    PrivateOrUnavailableError, RateLimitedError, classify_download_error, new_download_dir,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, MAX_ALBUM_ITEMS, classify_media_type,
)


def _extract_instagram_shortcode(url: str) -> Optional[str]:
    """
    يستخرج الـ shortcode من لينك بوست/ريل إنستجرام. لازم نقسم على
    '/reel/' أو '/reels/' بالكامل (مع الـ slash الأخير)، مش '/reel'
    لوحدها - كانت بتطلع string فاضي بدل الشورت كود الحقيقي.
    """
    if '/p/' in url:
        shortcode = url.split('/p/')[1].split('/')[0]
    elif '/reel/' in url:
        shortcode = url.split('/reel/')[1].split('/')[0]
    elif '/reels/' in url:
        shortcode = url.split('/reels/')[1].split('/')[0]
    else:
        return None
    shortcode = shortcode.split('?')[0].split('&')[0]
    return shortcode or None


class UniversalVideoDownloader:
    """Universal downloader for all major video platforms"""

    def __init__(self, output_dir: Optional[str] = None):
        # ✅ باگ كان موجود: نفس المشكلة اللي في youtube.py - مجلد مشترك بين
        # كل التحميلات، بالإضافة إن download_instagram_content كانت بتعتمد
        # على "قارن قبل/بعد" (before_files/after_files) على المجلد المشترك
        # ده عشان تلاقي الملف الجديد - ده مش آمن خالص لو تحميل تاني (لأي
        # مستخدم) شغال بالتوازي في نفس المجلد في نفس اللحظة، ممكن يرجع
        # ملف مستخدم تاني بالغلط. دلوقتي كل instance ليه مجلد فريد خاص بيه.
        self.output_dir = output_dir  # هيتحدد لما نحتاج نكتب فيه فعليًا
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    def _ensure_output_directory(self) -> str:
        if not self.output_dir:
            self.output_dir = new_download_dir()
        else:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def _make_progress_hook(self, progress_callback):
        """نفس فكرة الهوك في youtube.py - بيحول تحديثات yt-dlp لشكل بسيط لشريط التقدم"""
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

    def download_instagram_content(self, url: str) -> Optional[str]:
        """Download Instagram posts, reels, and stories"""
        try:
            print("[INSTAGRAM] Attempting to download...")
            self._ensure_output_directory()
            L = instaloader.Instaloader(
                quiet=False,
                user_agent=self.user_agent,
                download_videos=True,
                # ✅ كانت الإعدادات الافتراضية بتخلي instaloader يحمّل صور
                # thumbnail وملفات metadata (json/txt) كمان مش الفيديو بس -
                # ده كان بيسيب ملفات إضافية متراكمة في مجلد التحميلات.
                # دلوقتي بنعطلها كلها عشان يحمّل الفيديو بس.
                download_pictures=False,
                download_video_thumbnails=False,
                save_metadata=False,
                download_comments=False,
                post_metadata_txt_pattern='',
                max_connection_attempts=1,
            )

            shortcode = _extract_instagram_shortcode(url)
            if not shortcode:
                print("[ERROR] Invalid Instagram URL format / could not extract shortcode")
                return None

            post = instaloader.Post.from_shortcode(L.context, shortcode)

            # ✅ بما إن self.output_dir بقى مجلد فريد خاص بهذا التحميل بس
            # (مش مشترك مع باقي المستخدمين)، أي ملف فيديو موجود جواه بعد
            # التحميل هو ملفنا أكيد - مفيش داعي لمقارنة قبل/بعد اللي كانت
            # غير آمنة أصلاً لو تحميل تاني شغال بالتوازي في نفس المجلد.
            L.download_post(post, target=self.output_dir)
            video_files = sorted(
                glob.glob(os.path.join(self.output_dir, "*")),
                key=os.path.getmtime,
                reverse=True,
            )
            video_files = [f for f in video_files if f.lower().endswith((".mp4", ".mov", ".mkv"))]

            if video_files:
                print("[INSTAGRAM] Download successful")
                return video_files[0]

            print("[WARNING] Instagram post downloaded but no video file found (may be a photo post)")
            return None

        except (instaloader.exceptions.LoginRequiredException,
                instaloader.exceptions.PrivateProfileNotFollowedException) as e:
            # ✅ instaloader بيرفع الـ exceptions المحددة دي تحديدًا لما
            # البروفايل يكون خاص أو المنشور محتاج تسجيل دخول - أدق بكتير
            # من مطابقة نص رسالة الخطأ.
            raise PrivateOrUnavailableError(str(e)) from e

        except instaloader.exceptions.TooManyRequestsException as e:
            raise RateLimitedError(str(e)) from e

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Instagram download failed: {err_msg[:100]}")
            return None

    # ─────────────────────────────────────────────────────────
    # ✅ جديد: دعم الألبومات/الكاروسيل - بوست إنستجرام فيه أكتر من صورة
    # أو فيديو، عايزين نحمّلهم كلهم من نفس اللينك مرة واحدة بدل ما ناخد
    # أول فيديو بس.
    # ─────────────────────────────────────────────────────────
    def download_instagram_album(self, url: str) -> Optional[list]:
        """
        يحمّل كل عناصر بوست إنستجرام (صور + فيديوهات) - سواء كان عنصر
        واحد أو كاروسيل فيه عدة عناصر. بيرجع list من dicts بالشكل:
        [{"path": "...", "type": "photo"|"video"}, ...] بنفس ترتيب البوست
        الأصلي، أو None لو فشل التحميل بالكامل.
        """
        try:
            print("[INSTAGRAM][ALBUM] Attempting to download...")
            self._ensure_output_directory()
            
            shortcode = _extract_instagram_shortcode(url)
            if not shortcode:
                print("[ERROR] Invalid Instagram URL format / could not extract shortcode")
                return None
            
            try:
                L = instaloader.Instaloader(
                    quiet=False,
                    user_agent=self.user_agent,
                    download_videos=True,
                    download_pictures=True,
                    download_video_thumbnails=False,
                    save_metadata=False,
                    download_comments=False,
                    post_metadata_txt_pattern='',
                    max_connection_attempts=1,
                )
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=self.output_dir)
                
                media_files = sorted(
                    f for f in glob.glob(os.path.join(self.output_dir, "*"))
                    if f.lower().endswith(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)
                )
                if media_files:
                    media_files = media_files[:MAX_ALBUM_ITEMS]
                    items = [{"path": f, "type": classify_media_type(f)} for f in media_files]
                    print(f"[INSTAGRAM][ALBUM] Downloaded {len(items)} item(s) via Instaloader")
                    return items
            except Exception as e:
                print(f"[INSTALOADER ERROR] Failed: {e}, falling back to Cobalt API...")
            
            # ✅ Fallback: Try Cobalt API for Telegram bot
            import urllib.request
            import json
            import uuid
            
            instances = ["https://co.wuk.sh/api/json", "https://cobalt.kwiatekm.cc/api/json"]
            for inst in instances:
                try:
                    req = urllib.request.Request(inst)
                    req.add_header('Accept', 'application/json')
                    req.add_header('Content-Type', 'application/json')
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    payload = json.dumps({"url": url}).encode('utf-8')
                    resp = urllib.request.urlopen(req, data=payload, timeout=8)
                    cobalt_data = json.loads(resp.read().decode('utf-8'))
                    
                    media_items = []
                    urls_to_download = []
                    
                    if cobalt_data.get("status") == "picker":
                        for item in cobalt_data.get("picker", []):
                            urls_to_download.append(item.get("url"))
                    elif cobalt_data.get("status") in ["stream", "redirect"]:
                        urls_to_download.append(cobalt_data.get("url"))
                        
                    if not urls_to_download:
                        continue
                        
                    print(f"[COBALT] Extracting {len(urls_to_download)} items...")
                    urls_to_download = urls_to_download[:MAX_ALBUM_ITEMS]
                    
                    for idx, media_url in enumerate(urls_to_download):
                        is_vid = ".mp4" in media_url or "?ig_cache_key" not in media_url
                        ext = "mp4" if is_vid else "jpg"
                        filename = f"cobalt_ig_{shortcode}_{idx}_{uuid.uuid4().hex[:8]}.{ext}"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        dl_req = urllib.request.Request(media_url)
                        dl_req.add_header('User-Agent', 'Mozilla/5.0')
                        with urllib.request.urlopen(dl_req, timeout=30) as r, open(filepath, 'wb') as f:
                            f.write(r.read())
                        
                        media_items.append({"path": filepath, "type": classify_media_type(filepath)})
                        
                    if media_items:
                        print(f"[INSTAGRAM][ALBUM] Downloaded {len(media_items)} item(s) via Cobalt API")
                        return media_items
                except Exception as e:
                    print(f"[COBALT ERROR] {inst} failed: {e}")
                    continue

            print("[WARNING] Instagram album: post downloaded but no media files found")
            return None

        except (instaloader.exceptions.LoginRequiredException,
                instaloader.exceptions.PrivateProfileNotFollowedException) as e:
            raise PrivateOrUnavailableError(str(e)) from e

        except instaloader.exceptions.TooManyRequestsException as e:
            raise RateLimitedError(str(e)) from e

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Instagram album download failed: {err_msg[:100]}")
            return None

    def download_generic_album(self, url: str, progress_callback=None) -> Optional[list]:
        """
        دعم عام (best-effort) لبوستات متعددة العناصر في منصات غير
        إنستجرام (زي تغريدة فيها أكتر من صورة/فيديو، بورد بينتريست،
        ألبوم فيسبوك...) عن طريق yt-dlp لما بيرجع أكتر من "entry" لنفس
        اللينك. مش كل منصة بتدعم ده بنفس الاستقرار (مثلاً TikTok
        slideshow دعمها في yt-dlp لسه مش ثابت) - لو ملقناش أكتر من عنصر
        فعليًا، بترجع None وتسيب الاستدعاء يرجع للمسار العادي (تحميل
        فيديو واحد بس).
        """
        self._ensure_output_directory()
        ydl_opts = {
            'outtmpl': os.path.join(self.output_dir, '%(playlist_index,autonumber)s_%(id)s.%(ext)s'),
            'format': 'best[ext=mp4]/best[ext=webm]/best',
            'quiet': False,
            'socket_timeout': 50,
            'http_headers': {'User-Agent': self.user_agent},
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            # ✅ لو عنصر واحد جوه الألبوم فشل، منوقفش باقي التحميل بسببه
            'ignoreerrors': True,
            # ✅ حماية من لينكات playlist ضخمة (زي قناة يوتيوب كاملة)
            'playlistend': MAX_ALBUM_ITEMS,
            'progress_hooks': [self._make_progress_hook(progress_callback)],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("[YT-DLP][ALBUM] Starting album download...")
                info = ydl.extract_info(url, download=True)

                entries = list(info.get('entries') or []) if info else []
                entries = [e for e in entries if e]  # نشيل العناصر اللي فشلت (None بسبب ignoreerrors)

                if len(entries) < 2:
                    # مش ألبوم فعليًا (عنصر واحد بس أو مفيش entries أصلًا)
                    return None

                items = []
                for entry in entries:
                    path = None
                    requested = entry.get('requested_downloads') or []
                    if requested:
                        path = requested[0].get('filepath')
                    if not path:
                        try:
                            path = ydl.prepare_filename(entry)
                        except Exception:
                            path = None
                    if path and os.path.exists(path):
                        items.append({"path": path, "type": classify_media_type(path)})

                if len(items) < 2:
                    return None

                print(f"[YT-DLP][ALBUM] Downloaded {len(items)} item(s)")
                return items

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Generic album download failed: {err_msg[:100]}")
            return None

    def download_universal(self, url: str, progress_callback=None) -> Optional[str]:
        """Universal download using yt-dlp"""
        self._ensure_output_directory()

        ydl_opts = {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'format': 'best[ext=mp4]/best[ext=webm]/best',
            'quiet': False,
            'socket_timeout': 50,
            'http_headers': {
                'User-Agent': self.user_agent
            },
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'tv', 'android', 'mweb'],
                }
            },
            'progress_hooks': [self._make_progress_hook(progress_callback)],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"[YT-DLP] Starting download...")
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                if os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"[YT-DLP] Success! Size: {size_mb:.2f} MB")
                    return file_path
                else:
                    print("[ERROR] File not found after download")
                    return None

        except Exception as e:
            err_msg = str(e)
            kind = classify_download_error(err_msg)
            if kind == "private":
                raise PrivateOrUnavailableError(err_msg) from e
            if kind == "rate_limited":
                raise RateLimitedError(err_msg) from e
            print(f"[ERROR] Download failed: {err_msg[:100]}")
            return None

    def download(self, url: str, progress_callback=None) -> Optional[str]:
        """Smart download - tries Instagram first if applicable"""

        if 'instagram.com' in url:
            result = self.download_instagram_content(url)
            if result:
                return result
            print("[FALLBACK] Trying yt-dlp for Instagram...")

        return self.download_universal(url, progress_callback)

def download_from_any_platform(url: str, progress_callback=None) -> Optional[str]:
    """Main function to download from any platform"""
    downloader = UniversalVideoDownloader()
    return downloader.download(url, progress_callback)


def download_instagram_album(url: str) -> Optional[list]:
    """✅ جديد: يحمّل كل عناصر بوست إنستجرام (صورة واحدة، فيديو واحد، أو كاروسيل كامل)"""
    downloader = UniversalVideoDownloader()
    return downloader.download_instagram_album(url)


def download_generic_album(url: str, progress_callback=None) -> Optional[list]:
    """✅ جديد: تحميل ألبوم/بوست متعدد العناصر لمنصة غير إنستجرام (best-effort عبر yt-dlp)"""
    downloader = UniversalVideoDownloader()
    return downloader.download_generic_album(url, progress_callback)
