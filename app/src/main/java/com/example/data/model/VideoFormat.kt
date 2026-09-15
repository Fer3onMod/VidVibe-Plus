package com.example.data.model

data class VideoFormat(
    val formatId: String,
    val resolution: String,      // e.g., "1080p Full HD", "720p HD", "480p", "320kbps MP3"
    val qualityLabel: String,    // e.g., "1080p", "720p", "MP3"
    val container: String,       // e.g., "mp4", "mp3", "webm"
    val isAudioOnly: Boolean,
    val estimatedSizeBytes: Long,
    val directUrl: String,
    val videoCodec: String = "h264",
    val audioCodec: String = "aac"
) {
    val formattedSize: String
        get() {
            if (estimatedSizeBytes <= 0) return "Calculating..."
            val mb = estimatedSizeBytes / (1024.0 * 1024.0)
            return if (mb >= 1024.0) {
                String.format("%.2f GB", mb / 1024.0)
            } else {
                String.format("%.1f MB", mb)
            }
        }
}
