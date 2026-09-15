from pyrogram import filters, enums
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from keyboards import language_selection, main_menu, quality_menu
from youtube import (
    get_video_formats, download_video_with_quality, download_audio,
    detect_platform, is_platform_blocking_error
)
from multi_platform import download_from_any_platform, download_instagram_album, download_generic_album
from database import (
    touch_user, log_download, check_rate_limit, get_global_stats, get_user_stats,
    RATE_LIMIT_MAX
)
from utils import safe_delete_download_dir, escape_markdown, chunk_list, PrivateOrUnavailableError, RateLimitedError
import asyncio
import os
import re
import uuid

# user_data[chat_id] = {"url": str, "title": str, "qualities": [ {...}, ... ]}
user_data = {}
user_language = {}

translations = {
    "English": {
        "selected": "✅ English selected successfully!",
        "send_link": "📥 Send me any video link (YouTube, TikTok, Instagram, Twitter/X, Facebook...) and I'll handle the rest!",
        "fetching_info": "🔍 Analyzing link...",
        "select_quality": "📊 Choose the video quality:",
        "downloading": "⏳ Downloading...",
        "downloading_audio": "🎵 Extracting audio...",
        "download_success": "✅ Video downloaded successfully!",
        "audio_success": "✅ Audio downloaded successfully!",
        "download_error": "❌ Error downloading.",
        "invalid_url": "❌ Invalid URL! Please send a valid video link.",
        "what_next": "🔄 Send another link anytime!",
        "no_formats": "⚠️ Couldn't detect multiple qualities for this link, downloading the best available quality...",
        "content_blocked": "🚫 This content isn't available right now — it may require login, or the platform is temporarily rate-limiting requests. Please try again in a few minutes, or try a different link.",
        "cancelled": "❌ Cancelled.",
        "rate_limited": "⏳ You've reached the limit of {max} downloads/hour. Try again in {minutes} min.",
        "outdated_session": "⚠️ This request is outdated — you sent a newer link. Please use the buttons on your latest message.",
        "downloading_album": "⏳ Downloading album ({count} items)...",
        "album_success": "✅ Downloaded {count} items successfully!"
    },
    "Arabic": {
        "selected": "✅ تم اختيار اللغة العربية بنجاح!",
        "send_link": "📥 ابعتلي أي رابط فيديو (يوتيوب، تيك توك، إنستجرام، تويتر، فيسبوك...) وأنا هتصرف!",
        "fetching_info": "🔍 جاري تحليل الرابط...",
        "select_quality": "📊 اختر جودة الفيديو:",
        "downloading": "⏳ جاري التحميل...",
        "downloading_audio": "🎵 جاري استخراج الصوت...",
        "download_success": "✅ تم تحميل الفيديو بنجاح!",
        "audio_success": "✅ تم تحميل الصوت بنجاح!",
        "download_error": "❌ خطأ في التحميل.",
        "invalid_url": "❌ رابط غير صحيح! أرسل رابط فيديو حقيقي.",
        "what_next": "🔄 ابعت رابط تاني في أي وقت!",
        "no_formats": "⚠️ مقدرتش أجيب جودات متعددة لهذا الرابط، هحمّل بأفضل جودة متاحة...",
        "content_blocked": "🚫 المحتوى ده مش متاح دلوقتي - ممكن يكون محتاج تسجيل دخول، أو المنصة بتعمل حظر مؤقت للطلبات الكتير. جرب تاني بعد شوية، أو جرب رابط تاني.",
        "cancelled": "❌ تم الإلغاء.",
        "rate_limited": "⏳ وصلت للحد الأقصى ({max} تحميلات في الساعة). حاول تاني بعد {minutes} دقيقة.",
        "outdated_session": "⚠️ الطلب ده قديم - أنت بعتت رابط جديد بعده. استخدم أزرار آخر رسالة بعتها.",
        "downloading_album": "⏳ جاري تحميل الألبوم ({count} عنصر)...",
        "album_success": "✅ تم تحميل {count} عنصر بنجاح!"
    },
    "French": {
        "selected": "✅ Français sélectionné avec succès!",
        "send_link": "📥 Envoyez-moi n'importe quel lien vidéo (YouTube, TikTok, Instagram, Twitter/X, Facebook...) et je m'occupe du reste!",
        "fetching_info": "🔍 Analyse du lien...",
        "select_quality": "📊 Choisissez la qualité vidéo:",
        "downloading": "⏳ Téléchargement en cours...",
        "downloading_audio": "🎵 Extraction de l'audio...",
        "download_success": "✅ Vidéo téléchargée avec succès!",
        "audio_success": "✅ Audio téléchargé avec succès!",
        "download_error": "❌ Erreur de téléchargement.",
        "invalid_url": "❌ URL invalide! Envoyez un lien vidéo valide.",
        "what_next": "🔄 Envoyez un autre lien à tout moment!",
        "no_formats": "⚠️ Impossible de détecter plusieurs qualités pour ce lien, téléchargement de la meilleure qualité...",
        "content_blocked": "🚫 Ce contenu n'est pas disponible pour le moment — connexion requise ou limitation temporaire de la plateforme. Réessayez dans quelques minutes ou essayez un autre lien.",
        "cancelled": "❌ Annulé.",
        "rate_limited": "⏳ Vous avez atteint la limite de {max} téléchargements/heure. Réessayez dans {minutes} min.",
        "outdated_session": "⚠️ Cette demande est obsolète — vous avez envoyé un lien plus récent. Utilisez les boutons de votre dernier message.",
        "downloading_album": "⏳ Téléchargement de l'album ({count} éléments)...",
        "album_success": "✅ {count} éléments téléchargés avec succès!"
    },
    "German": {
        "selected": "✅ Deutsch erfolgreich ausgewählt!",
        "send_link": "📥 Sende mir einen Video-Link (YouTube, TikTok, Instagram, Twitter/X, Facebook...) und ich kümmere mich um den Rest!",
        "fetching_info": "🔍 Link wird analysiert...",
        "select_quality": "📊 Videoqualität wählen:",
        "downloading": "⏳ Download läuft...",
        "downloading_audio": "🎵 Audio wird extrahiert...",
        "download_success": "✅ Video erfolgreich heruntergeladen!",
        "audio_success": "✅ Audio erfolgreich heruntergeladen!",
        "download_error": "❌ Download-Fehler.",
        "invalid_url": "❌ Ungültige URL! Senden Sie einen gültigen Video-Link.",
        "what_next": "🔄 Sende jederzeit einen weiteren Link!",
        "no_formats": "⚠️ Mehrere Qualitäten konnten nicht erkannt werden, beste verfügbare Qualität wird heruntergeladen...",
        "content_blocked": "🚫 Dieser Inhalt ist gerade nicht verfügbar — eventuell ist eine Anmeldung nötig, oder die Plattform begrenzt vorübergehend die Anfragen. Bitte in ein paar Minuten erneut versuchen oder einen anderen Link probieren.",
        "cancelled": "❌ Abgebrochen.",
        "rate_limited": "⏳ Sie haben das Limit von {max} Downloads/Stunde erreicht. Versuchen Sie es in {minutes} Min. erneut.",
        "outdated_session": "⚠️ Diese Anfrage ist veraltet — Sie haben einen neueren Link gesendet. Bitte die Schaltflächen Ihrer letzten Nachricht verwenden.",
        "downloading_album": "⏳ Album wird heruntergeladen ({count} Elemente)...",
        "album_success": "✅ {count} Elemente erfolgreich heruntergeladen!"
    },
    "Russian": {
        "selected": "✅ Русский успешно выбран!",
        "send_link": "📥 Отправьте мне любую ссылку на видео (YouTube, TikTok, Instagram, Twitter/X, Facebook...) и я всё сделаю!",
        "fetching_info": "🔍 Анализ ссылки...",
        "select_quality": "📊 Выберите качество видео:",
        "downloading": "⏳ Загрузка...",
        "downloading_audio": "🎵 Извлечение аудио...",
        "download_success": "✅ Видео успешно загружено!",
        "audio_success": "✅ Аудио успешно загружено!",
        "download_error": "❌ Ошибка загрузки.",
        "invalid_url": "❌ Неверная ссылка! Отправьте действительную ссылку на видео.",
        "what_next": "🔄 Отправьте другую ссылку в любое время!",
        "no_formats": "⚠️ Не удалось определить несколько качеств, загрузка в лучшем доступном качестве...",
        "content_blocked": "🚫 Этот контент сейчас недоступен — возможно, требуется вход в аккаунт, или платформа временно ограничивает запросы. Попробуйте через несколько минут или используйте другую ссылку.",
        "cancelled": "❌ Отменено.",
        "rate_limited": "⏳ Вы достигли лимита {max} загрузок/час. Повторите через {minutes} мин.",
        "outdated_session": "⚠️ Этот запрос устарел — вы отправили более новую ссылку. Используйте кнопки последнего сообщения.",
        "downloading_album": "⏳ Загрузка альбома ({count} элементов)...",
        "album_success": "✅ Успешно загружено {count} элементов!"
    }
}


def is_valid_url(text):
    """Check if text is a valid URL"""
    url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    return re.match(url_pattern, text) is not None


async def safe_edit_text(callback_query, text, reply_markup=None):
    """Safely edit message text without MESSAGE_NOT_MODIFIED error"""
    try:
        current_text = callback_query.message.text or ""
        if current_text != text:
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        print(f"[WARNING] Could not edit message: {str(e)[:50]}")


def _make_progress_updater(loop, status_message, prefix_text: str = "⏳"):
    """
    بيبني دالة callback بتتنفذ جوه ثريد التحميل (sync) وتحدّث رسالة تيليجرام (async)
    بشريط تقدم حقيقي، بس كل 10% عشان منضربش limits التعديل بتاعة تيليجرام.
    """
    last_percent = {"value": -1}

    def callback(info):
        if info.get("status") != "downloading":
            return

        percent = info.get("percent", 0)
        # حدّث بس لما نعدي عتبة كل 10% (أو أول مرة)
        if percent - last_percent["value"] < 10 and percent < 99:
            return
        last_percent["value"] = percent

        bar_len = 10
        filled = min(bar_len, int(percent / 100 * bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)
        speed_mb = (info.get("speed") or 0) / (1024 * 1024)
        downloaded_mb = info.get("downloaded_mb", 0)
        total_mb = info.get("total_mb", 0)

        text = (
            f"{prefix_text}\n"
            f"{bar} {percent:.0f}%\n"
            f"📦 {downloaded_mb:.1f}MB / {total_mb:.1f}MB"
            + (f"  •  {speed_mb:.1f} MB/s" if speed_mb else "")
        )

        # ✅ بننشئ الـ coroutine جوه دالة async حقيقية معرّفة عندنا، عشان نضمن إنها
        # coroutine صحيحة 100% مهما كان نوع edit_text الراجع من pyrogram،
        # وعشان منستدعيش .edit_text() نفسها من غير الـ event loop thread.
        async def _do_edit():
            await status_message.edit_text(text)

        try:
            future = asyncio.run_coroutine_threadsafe(_do_edit(), loop)
        except Exception as e:
            print(f"[WARNING] Progress update failed: {str(e)[:60]}")
            return

        def _log_future_error(fut):
            try:
                fut.result()
            except Exception as e:
                print(f"[WARNING] Progress edit failed: {str(e)[:60]}")

        future.add_done_callback(_log_future_error)

    return callback


async def _send_album_and_cleanup(client, chat_id, status_msg, lang, url, platform, items):
    """
    ✅ جديد: يبعت عناصر ألبوم/كاروسيل (صور و/أو فيديوهات) للمستخدم،
    يسجلهم في قاعدة البيانات، وينضف الملفات من السيرفر بعد كده.
    - عنصر واحد بس: بيتبعت عادي بـ send_photo/send_video (نفس شكل
      تحميل عادي).
    - أكتر من عنصر: بيتبعتوا كـ send_media_group، مقسّمين لمجموعات من
      10 عناصر بالظبط (الحد الأقصى المسموح بيه من تيليجرام لكل رسالة).
    """
    count = len(items)
    album_id = uuid.uuid4().hex if count > 1 else None

    try:
        if count == 1:
            item = items[0]
            size_mb = os.path.getsize(item["path"]) / (1024 * 1024)
            if item["type"] == "photo":
                await client.send_photo(chat_id, item["path"], caption=translations[lang]["download_success"])
            else:
                await client.send_video(chat_id, item["path"], caption=translations[lang]["download_success"])
            await asyncio.to_thread(log_download, chat_id, platform, item["type"], url, size_mb)
        else:
            caption_sent = False
            for chunk in chunk_list(items, 10):
                media_group = []
                for item in chunk:
                    media_cls = InputMediaPhoto if item["type"] == "photo" else InputMediaVideo
                    # ✅ الكابشن بيتحط على أول عنصر في أول مجموعة بس -
                    # تيليجرام بيعرضه كوصف للألبوم كله على أي حال.
                    if not caption_sent:
                        media_group.append(media_cls(item["path"], caption=translations[lang]["album_success"].format(count=count)))
                        caption_sent = True
                    else:
                        media_group.append(media_cls(item["path"]))
                await client.send_media_group(chat_id, media_group)

            for item in items:
                size_mb = os.path.getsize(item["path"]) / (1024 * 1024)
                await asyncio.to_thread(
                    log_download, chat_id, platform, item["type"], url, size_mb, album_id, count
                )

        await status_msg.delete()
        await client.send_message(chat_id, translations[lang]["what_next"])
        print(f"[SUCCESS] Album sent to user {chat_id}: {count} item(s)")

    except Exception as e:
        await status_msg.edit_text(f"{translations[lang]['download_error']}\n{str(e)[:100]}")
        print(f"[ERROR] Sending album failed: {str(e)[:100]}")

    finally:
        # ✅ تنظيف: كل عناصر الألبوم في نفس مجلد التحميل الفريد، فمسح
        # مجلد أول عنصر كفاية لمسح المجلد بالكامل
        if items:
            safe_delete_download_dir(items[0]["path"])


def setup_handlers(app):

    @app.on_message(filters.command("start"))
    async def start(client, message: Message):
        chat_id = message.chat.id
        user = message.from_user
        raw_username = f"@{user.username}" if user.username else (user.first_name or "")
        # ✅ باگ كان موجود: الاسم ده بيتحقن جوه رسالة بترسل بـ
        # parse_mode=MARKDOWN. لو فيه رمز زي _ أو * في first_name (شائع
        # جدًا)، تيليجرام كان بيرفض الرسالة بخطأ "Can't parse entities".
        username = escape_markdown(raw_username)

        user_language[chat_id] = None
        user_data.pop(chat_id, None)
        await asyncio.to_thread(touch_user, chat_id)

        welcome_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 Welcome, {username}!
🤖 Video Downloader Bot v2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 Just send a link from:
  • YouTube & Shorts
  • TikTok
  • Instagram & Reels
  • Twitter/X
  • Facebook
  • Pinterest
  • And more...

📦 Got a post with multiple photos/videos (like an Instagram carousel)? Send its link and I'll download all of them at once!

I detect the platform automatically 🚀

🌍 Choose your language:
"""

        await message.reply_text(
            welcome_text,
            reply_markup=language_selection(),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        print(f"[USER] {raw_username} started the bot")

    @app.on_message(filters.command("stats"))
    async def stats_command(client, message: Message):
        chat_id = message.chat.id
        lang = user_language.get(chat_id) or "English"

        g = await asyncio.to_thread(get_global_stats)
        u = await asyncio.to_thread(get_user_stats, chat_id)
        platform_lines = "\n".join(
            f"  • {p}: {c}" for p, c in g["by_platform"]
        ) or "  -"

        text = (
            "📊 **Bot Stats**\n\n"
            f"🌍 Total downloads: {g['total_downloads']}\n"
            f"👥 Total users: {g['total_users']}\n"
            f"💾 Total data transferred: {g['total_mb']:.1f} MB\n\n"
            f"📈 By platform:\n{platform_lines}\n\n"
            f"👤 Your downloads: {u['total_downloads']}"
        )
        await message.reply_text(text, parse_mode=enums.ParseMode.MARKDOWN)

    @app.on_callback_query()
    async def callback_query_handler(client, callback_query: CallbackQuery):
        data = callback_query.data
        chat_id = callback_query.message.chat.id
        lang = user_language.get(chat_id) or "English"

        languages = {
            "lang_en": "English",
            "lang_ar": "Arabic",
            "lang_fr": "French",
            "lang_de": "German",
            "lang_ru": "Russian"
        }

        # ── اختيار اللغة ──
        if data in languages:
            user_language[chat_id] = languages[data]
            lang = languages[data]
            await safe_edit_text(
                callback_query,
                f"{translations[lang]['selected']}\n\n{translations[lang]['send_link']}",
                reply_markup=main_menu(lang)
            )
            print(f"[LANGUAGE] User selected: {lang}")
            return

        # ── تغيير اللغة ──
        if data == "back":
            await safe_edit_text(
                callback_query,
                "🌍 Choose your language:",
                reply_markup=language_selection()
            )
            return

        # ── إلغاء ──
        if data == "cancel":
            user_data.pop(chat_id, None)
            await safe_edit_text(callback_query, translations[lang]["cancelled"])
            return

        # ── اختيار الجودة أو الصوت (لازم يكون فيه سيشن مخزّن) ──
        session = user_data.get(chat_id)
        if not session:
            await safe_edit_text(callback_query, translations[lang]["cancelled"])
            return

        # ✅ لو الرسالة اللي اتضغط عليها مش هي آخر رسالة قائمة جودات بعتناها
        # (يعني المستخدم بعت رابط جديد بعدها) - منكملش، عشان منحملش فيديو
        # غلط باسم الرابط القديم. شوف التعليق فوق عند تخزين menu_message_id.
        if session.get("menu_message_id") != callback_query.message.id:
            await safe_edit_text(callback_query, translations[lang]["outdated_session"])
            return

        url = session["url"]
        loop = asyncio.get_running_loop()

        # 🎵 تحميل الصوت فقط
        if data == "audio":
            await safe_edit_text(callback_query, translations[lang]["downloading_audio"])
            progress_cb = _make_progress_updater(
                loop, callback_query.message, translations[lang]["downloading_audio"]
            )
            file_path = None
            try:
                file_path = await asyncio.to_thread(download_audio, url, progress_cb)
                if file_path and os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    await client.send_audio(
                        chat_id,
                        file_path,
                        caption=translations[lang]["audio_success"],
                        title=session.get("title", "audio")
                    )
                    await asyncio.to_thread(log_download, chat_id, detect_platform(url), "audio", url, size_mb)
                    await callback_query.message.delete()
                    await client.send_message(chat_id, translations[lang]["what_next"])
                else:
                    await safe_edit_text(callback_query, translations[lang]["download_error"])
            except (PrivateOrUnavailableError, RateLimitedError) as e:
                await safe_edit_text(callback_query, translations[lang]["content_blocked"])
                print(f"[BLOCKED] Audio download blocked: {str(e)[:100]}")
            except Exception as e:
                await safe_edit_text(
                    callback_query,
                    f"{translations[lang]['download_error']}\n{str(e)[:100]}"
                )
                print(f"[ERROR] Audio download failed: {str(e)[:100]}")
            finally:
                # ✅ تنظيف: نمسح الملف من السيرفر بعد الإرسال عشان نوفر مساحة
                safe_delete_download_dir(file_path)
                user_data.pop(chat_id, None)
            return

        # 🎞 تحميل بجودة محددة
        if data.startswith("q_"):
            try:
                idx = int(data.split("_", 1)[1])
                quality = session["qualities"][idx]
            except (ValueError, IndexError):
                await safe_edit_text(callback_query, translations[lang]["download_error"])
                user_data.pop(chat_id, None)
                return

            await safe_edit_text(callback_query, translations[lang]["downloading"])
            progress_cb = _make_progress_updater(
                loop, callback_query.message, translations[lang]["downloading"]
            )
            file_path = None
            try:
                file_path = await asyncio.to_thread(
                    download_video_with_quality, url, quality, progress_cb
                )
                if file_path and os.path.exists(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"[SUCCESS] Downloaded: {size_mb:.2f} MB")
                    await client.send_video(
                        chat_id,
                        file_path,
                        caption=translations[lang]["download_success"]
                    )
                    await asyncio.to_thread(log_download, chat_id, detect_platform(url), "video", url, size_mb)
                    await callback_query.message.delete()
                    await client.send_message(chat_id, translations[lang]["what_next"])
                    print(f"[SUCCESS] Video sent to user {chat_id}")
                else:
                    await safe_edit_text(callback_query, translations[lang]["download_error"])
                    print("[ERROR] File not found after download")
            except (PrivateOrUnavailableError, RateLimitedError) as e:
                await safe_edit_text(callback_query, translations[lang]["content_blocked"])
                print(f"[BLOCKED] Video download blocked: {str(e)[:100]}")
            except Exception as e:
                await safe_edit_text(
                    callback_query,
                    f"{translations[lang]['download_error']}\n{str(e)[:100]}"
                )
                print(f"[ERROR] Video download failed: {str(e)[:100]}")
            finally:
                # ✅ تنظيف: نمسح الملف من السيرفر بعد الإرسال عشان نوفر مساحة
                safe_delete_download_dir(file_path)
                user_data.pop(chat_id, None)
            return

    @app.on_message(filters.text & ~filters.regex(r'^/'))
    async def handle_video_url(client, message: Message):
        chat_id = message.chat.id
        url = message.text.strip()
        lang = user_language.get(chat_id) or "English"

        # ✅ لازم رابط صحيح
        if not is_valid_url(url):
            await message.reply_text(translations[lang]["invalid_url"])
            print(f"[ERROR] Invalid URL received: {url[:50]}")
            return

        # ✅ حد الاستخدام (Rate Limiting) - قبل ما نستهلك أي موارد
        allowed, remaining, reset_in = await asyncio.to_thread(check_rate_limit, chat_id)
        if not allowed:
            minutes = max(1, reset_in // 60)
            await message.reply_text(
                translations[lang]["rate_limited"].format(max=RATE_LIMIT_MAX, minutes=minutes)
            )
            print(f"[RATE_LIMIT] Blocked user {chat_id}, reset in {reset_in}s")
            return

        print(f"[URL_RECEIVED] {url[:60]}... (remaining: {remaining})")
        status_msg = await message.reply_text(translations[lang]["fetching_info"])

        # ✅ جديد: بوستات إنستجرام (لينكات /p/ و /reel/ و /reels/) بتتعامل
        # في مسار منفصل تمامًا عن مسار yt-dlp تحت - أولًا لأن yt-dlp مش
        # موثوق فيه مع إنستجرام غالبًا (بيحتاج لوجين)، وثانيًا عشان نقدر
        # ندعم بوستات الكاروسيل (أكتر من صورة/فيديو في بوست واحد)
        # باستخدام instaloader اللي بيدعمها أصلًا. كده بنوفر كمان محاولة
        # get_video_formats الفاشلة غالبًا لإنستجرام.
        if 'instagram.com' in url and any(seg in url for seg in ('/p/', '/reel/', '/reels/')):
            await status_msg.edit_text(translations[lang]["downloading"])
            items = None
            try:
                items = await asyncio.to_thread(download_instagram_album, url)
            except (PrivateOrUnavailableError, RateLimitedError) as e:
                await status_msg.edit_text(translations[lang]["content_blocked"])
                print(f"[BLOCKED] Instagram album blocked: {str(e)[:100]}")
                return
            except Exception as e:
                await status_msg.edit_text(f"{translations[lang]['download_error']}\n{str(e)[:100]}")
                print(f"[ERROR] Instagram album failed: {str(e)[:100]}")
                return

            if not items:
                await status_msg.edit_text(translations[lang]["download_error"])
                print("[ERROR] Instagram album: no items downloaded")
                return

            await _send_album_and_cleanup(client, chat_id, status_msg, lang, url, "Instagram", items)
            return

        # ✅ اكتشاف الجودات المتاحة (بدون تحميل) - في thread منفصل عشان ميعطلش الـ event loop
        try:
            info, format_error = await asyncio.to_thread(get_video_formats, url)
        except Exception as e:
            info, format_error = None, str(e)
            print(f"[WARNING] Format detection error: {str(e)[:100]}")

        # ✅ جديد: لو اللينك ده بوست متعدد العناصر في منصة غير إنستجرام
        # (زي تغريدة فيها أكتر من صورة/فيديو) - نحاول نحمّل كل العناصر
        # كألبوم واحد. لو فشل فعليًا (رجع أقل من عنصرين)، منوقفش - بنكمل
        # عادي على المسار الاحتياطي (تحميل فيديو واحد) تحت.
        if info and info.get("is_album"):
            album_count = info.get("album_count", 0)
            await status_msg.edit_text(translations[lang]["downloading_album"].format(count=album_count))
            print(f"[ALBUM] Detected {album_count} items for {url[:40]}")

            loop = asyncio.get_running_loop()
            progress_cb = _make_progress_updater(
                loop, status_msg, translations[lang]["downloading_album"].format(count=album_count)
            )
            try:
                album_items = await asyncio.to_thread(download_generic_album, url, progress_cb)
            except (PrivateOrUnavailableError, RateLimitedError) as e:
                await status_msg.edit_text(translations[lang]["content_blocked"])
                print(f"[BLOCKED] Album blocked: {str(e)[:100]}")
                return
            except Exception as e:
                await status_msg.edit_text(f"{translations[lang]['download_error']}\n{str(e)[:100]}")
                print(f"[ERROR] Album download failed: {str(e)[:100]}")
                return

            if album_items:
                await _send_album_and_cleanup(
                    client, chat_id, status_msg, lang, url, detect_platform(url), album_items
                )
                return
            print("[ALBUM] Fallback to single-item path (album download returned <2 items)")

        # ✅ لو لقينا جودات متعددة، اعرضها للمستخدم (من الأقل للأعلى + صوت)
        if info and info.get("qualities"):
            title_preview = (info.get("title") or "")[:60]
            await status_msg.edit_text(
                f"{translations[lang]['select_quality']}\n\n🎬 {title_preview}",
                reply_markup=quality_menu(lang, info["qualities"])
            )
            # ✅ باگ كان موجود: لو المستخدم بعت رابط تاني قبل ما يختار جودة
            # الرابط الأول، user_data[chat_id] كانت بتتكتب فوق بالكامل.
            # فلو ضغط بعد كده على أزرار الرسالة "القديمة" (بتاعة الرابط
            # الأول)، كان البوت بيستخدم url الجلسة الحالية (الرابط التاني)
            # بالغلط - يعني ممكن يحمّل فيديو مختلف تمامًا عن اللي شايفه في
            # الرسالة. بنخزن هنا id رسالة القائمة نفسها، وبنتأكد في الـ
            # callback إن الرسالة اللي اتضغط عليها هي أحدث رسالة فعلاً.
            user_data[chat_id] = {
                "url": url,
                "title": info.get("title", "video"),
                "qualities": info["qualities"],
                "menu_message_id": status_msg.id,
            }
            print(f"[QUALITIES] Found {len(info['qualities'])} qualities for {url[:40]}")
            return

        # 🚫 المنصة (غالبًا Instagram) رافضة الطلب فعليًا - محتاجة لوجين أو
        # عاملة rate limit. هنا منحاولش تاني بطريقة تانية فورًا (ده كان
        # بيضرب Instagram 3 مرات متتالية لنفس الرابط ويزوّد الحظر) - بس
        # نبلّغ المستخدم برسالة واضحة.
        if is_platform_blocking_error(format_error):
            await status_msg.edit_text(translations[lang]["content_blocked"])
            print(f"[BLOCKED] {detect_platform(url)} rejected the request: {(format_error or '')[:100]}")
            return

        # ⚠️ Fallback: منصات ما بتديش جودات متعددة بسهولة (زي Instagram أحيانًا)
        await status_msg.edit_text(translations[lang]["no_formats"])
        print("[FALLBACK] No selectable qualities, using automatic best-quality download")

        loop = asyncio.get_running_loop()
        progress_cb = _make_progress_updater(loop, status_msg, translations[lang]["downloading"])
        file_path = None

        try:
            file_path = await asyncio.to_thread(download_from_any_platform, url, progress_cb)

            if file_path and os.path.exists(file_path):
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                print(f"[SUCCESS] Downloaded: {file_size_mb:.2f} MB")
                await client.send_video(
                    chat_id,
                    file_path,
                    caption=translations[lang]["download_success"]
                )
                await asyncio.to_thread(log_download, chat_id, detect_platform(url), "video", url, file_size_mb)
                await status_msg.delete()
                await message.reply_text(translations[lang]["what_next"])
                print(f"[SUCCESS] Video sent to user {chat_id}")
            else:
                await status_msg.edit_text(translations[lang]["download_error"])
                print("[ERROR] File not found after download")

        except (PrivateOrUnavailableError, RateLimitedError) as e:
            await status_msg.edit_text(translations[lang]["content_blocked"])
            print(f"[BLOCKED] Fallback download blocked: {str(e)[:100]}")

        except Exception as e:
            await status_msg.edit_text(
                f"{translations[lang]['download_error']}\n{str(e)[:100]}"
            )
            print(f"[ERROR] Download failed: {str(e)[:100]}")

        finally:
            # ✅ تنظيف: نمسح الملف من السيرفر بعد الإرسال عشان نوفر مساحة
            safe_delete_download_dir(file_path)
