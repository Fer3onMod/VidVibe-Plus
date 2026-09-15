package com.example.data.model

data class VideoMetadata(
    val id: String,
    val title: String,
    val author: String,
    val durationSeconds: Long,
    val thumbnailUrl: String?,
    val originalUrl: String,
    val platform: PlatformType,
    val availableFormats: List<VideoFormat>
) {
    val formattedDuration: String
        get() {
            if (durationSeconds <= 0) return ""
            val minutes = durationSeconds / 60
            val remainingSeconds = durationSeconds % 60
            val hours = minutes / 60
            val remMinutes = minutes % 60
            return if (hours > 0) {
                String.format("%d:%02d:%02d", hours, remMinutes, remainingSeconds)
            } else {
                String.format("%d:%02d", remMinutes, remainingSeconds)
            }
        }
}
