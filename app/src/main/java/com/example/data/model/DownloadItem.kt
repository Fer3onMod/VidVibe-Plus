package com.example.data.model

enum class DownloadStatus {
    QUEUED,
    DOWNLOADING,
    PAUSED,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class DownloadItem(
    val id: String,
    val originalUrl: String,
    val downloadUrl: String,
    val title: String,
    val author: String,
    val thumbnailUrl: String?,
    val formatLabel: String,
    val container: String,
    val isAudioOnly: Boolean,
    val localFilePath: String? = null,
    val mediaStoreUri: String? = null,
    val totalBytes: Long = 0,
    val downloadedBytes: Long = 0,
    val speedBytesPerSec: Long = 0,
    val status: DownloadStatus = DownloadStatus.QUEUED,
    val errorMessage: String? = null,
    val platform: PlatformType = PlatformType.UNIVERSAL,
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null
) {
    val progressPercent: Int
        get() = if (totalBytes > 0) {
            ((downloadedBytes.toDouble() / totalBytes.toDouble()) * 100).toInt().coerceIn(0, 100)
        } else {
            0
        }

    val formattedSpeed: String
        get() {
            if (status != DownloadStatus.DOWNLOADING || speedBytesPerSec <= 0) return "--"
            val kb = speedBytesPerSec / 1024.0
            val mb = kb / 1024.0
            return if (mb >= 1.0) {
                String.format("%.1f MB/s", mb)
            } else {
                String.format("%.0f KB/s", kb)
            }
        }

    val formattedDownloaded: String
        get() {
            val mbDownloaded = downloadedBytes / (1024.0 * 1024.0)
            val mbTotal = totalBytes / (1024.0 * 1024.0)
            return if (totalBytes > 0) {
                String.format("%.1f / %.1f MB", mbDownloaded, mbTotal)
            } else {
                String.format("%.1f MB", mbDownloaded)
            }
        }
}
