package com.example.data.model

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Audiotrack
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material.icons.filled.PushPin
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector

enum class PlatformType(
    val displayName: String,
    val brandColor: Color,
    val iconVector: ImageVector,
    val domainKeywords: List<String>
) {
    YOUTUBE(
        displayName = "YouTube",
        brandColor = Color(0xFFFF0000),
        iconVector = Icons.Filled.PlayCircle,
        domainKeywords = listOf("youtube.com", "youtu.be")
    ),
    YOUTUBE_SHORTS(
        displayName = "YT Shorts",
        brandColor = Color(0xFFFF2244),
        iconVector = Icons.Filled.PlayCircle,
        domainKeywords = listOf("youtube.com/shorts", "youtu.be/shorts")
    ),
    INSTAGRAM(
        displayName = "Instagram",
        brandColor = Color(0xFFE1306C),
        iconVector = Icons.Filled.VideoLibrary,
        domainKeywords = listOf("instagram.com", "instagr.am")
    ),
    TIKTOK(
        displayName = "TikTok",
        brandColor = Color(0xFF00F2FE),
        iconVector = Icons.Filled.PlayCircle,
        domainKeywords = listOf("tiktok.com", "vm.tiktok.com")
    ),
    TWITTER_X(
        displayName = "Twitter / X",
        brandColor = Color(0xFF1DA1F2),
        iconVector = Icons.Filled.Share,
        domainKeywords = listOf("twitter.com", "x.com", "t.co")
    ),
    FACEBOOK(
        displayName = "Facebook",
        brandColor = Color(0xFF1877F2),
        iconVector = Icons.Filled.VideoLibrary,
        domainKeywords = listOf("facebook.com", "fb.watch", "fb.com")
    ),
    TELEGRAM(
        displayName = "Telegram",
        brandColor = Color(0xFF229ED9),
        iconVector = Icons.Filled.Share,
        domainKeywords = listOf("t.me", "telegram.me")
    ),
    WHATSAPP(
        displayName = "WhatsApp",
        brandColor = Color(0xFF25D366),
        iconVector = Icons.Filled.Share,
        domainKeywords = listOf("whatsapp.com", "wa.me")
    ),
    PINTEREST(
        displayName = "Pinterest",
        brandColor = Color(0xFFE60023),
        iconVector = Icons.Filled.PushPin,
        domainKeywords = listOf("pinterest.com", "pin.it", "pinterest.co.uk", "pinterest.ca", "pinterest.fr", "pinterest.de")
    ),
    UNIVERSAL(
        displayName = "Direct Link",
        brandColor = Color(0xFF8B5CF6),
        iconVector = Icons.Filled.VideoLibrary,
        domainKeywords = emptyList()
    );

    companion object {
        fun detect(url: String): PlatformType {
            val lower = url.lowercase().trim()
            if (lower.contains("youtube.com/shorts") || lower.contains("youtu.be/shorts")) {
                return YOUTUBE_SHORTS
            }
            for (type in entries) {
                if (type == UNIVERSAL || type == YOUTUBE_SHORTS) continue
                if (type.domainKeywords.any { lower.contains(it) }) {
                    return type
                }
            }
            return UNIVERSAL
        }
    }
}
