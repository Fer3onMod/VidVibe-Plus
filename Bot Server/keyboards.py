from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_selection():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")
        ],
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])


def main_menu(language):
    """
    ✅ بعد إزالة قائمة اختيار المنصة، القائمة الرئيسية بقت بس فيها
    زرار تغيير اللغة. المستخدم بيبعت الرابط مباشرة والبوت بيكتشف المنصة لوحده.
    """
    change_lang_label = {
        "English": "🔄 Change Language",
        "Arabic": "🔄 تغيير اللغة",
        "French": "🔄 Changer de langue",
        "German": "🔄 Sprache ändern",
        "Russian": "🔄 Изменить язык"
    }.get(language, "🔄 Change Language")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(change_lang_label, callback_data="back")]
    ])


def quality_menu(language, qualities):
    """
    ✅ قائمة اختيار جودة الفيديو - مرتبة من الأقل للأعلى
    qualities: list of dicts -> {height, format_id, ext, filesize, has_audio}
    كل اختيار بيتحول لـ callback_data بصيغة q_<index> عشان نفضل جوه حدود الـ 64 بايت
    """
    buttons = []
    for idx, q in enumerate(qualities):
        size_mb = q.get("filesize", 0) / (1024 * 1024) if q.get("filesize") else 0
        size_str = f" (~{size_mb:.1f}MB)" if size_mb else ""
        label = f"🎞 {q['height']}p{size_str}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"q_{idx}")])

    audio_label = {
        "English": "🎵 Audio Only (MP3)",
        "Arabic": "🎵 صوت فقط (MP3)",
        "French": "🎵 Audio seulement (MP3)",
        "German": "🎵 Nur Audio (MP3)",
        "Russian": "🎵 Только аудио (MP3)"
    }.get(language, "🎵 Audio Only (MP3)")
    buttons.append([InlineKeyboardButton(audio_label, callback_data="audio")])

    cancel_label = {
        "English": "❌ Cancel",
        "Arabic": "❌ إلغاء",
        "French": "❌ Annuler",
        "German": "❌ Abbrechen",
        "Russian": "❌ Отмена"
    }.get(language, "❌ Cancel")
    buttons.append([InlineKeyboardButton(cancel_label, callback_data="cancel")])

    return InlineKeyboardMarkup(buttons)
