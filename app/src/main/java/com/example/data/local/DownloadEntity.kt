package com.example.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.example.data.model.DownloadItem
import com.example.data.model.DownloadStatus
import com.example.data.model.PlatformType

@Entity(tableName = "downloads")
data class DownloadEntity(
    @PrimaryKey
    val id: String,
    val originalUrl: String,
    val downloadUrl: String,
    val title: String,
    val author: String,
    val thumbnailUrl: String?,
    val formatLabel: String,
    val container: String,
    val isAudioOnly: Boolean,
    val localFilePath: String?,
    val mediaStoreUri: String?,
    val totalBytes: Long,
    val downloadedBytes: Long,
    val speedBytesPerSec: Long,
    val status: String,
    val errorMessage: String?,
    val platform: String,
    val createdAt: Long,
    val completedAt: Long?
) {
    fun toDownloadItem(): DownloadItem {
        val downloadStatus = try {
            DownloadStatus.valueOf(status)
        } catch (_: Exception) {
            DownloadStatus.FAILED
        }
        val platformType = try {
            PlatformType.valueOf(platform)
        } catch (_: Exception) {
            PlatformType.UNIVERSAL
        }

        return DownloadItem(
            id = id,
            originalUrl = originalUrl,
            downloadUrl = downloadUrl,
            title = title,
            author = author,
            thumbnailUrl = thumbnailUrl,
            formatLabel = formatLabel,
            container = container,
            isAudioOnly = isAudioOnly,
            localFilePath = localFilePath,
            mediaStoreUri = mediaStoreUri,
            totalBytes = totalBytes,
            downloadedBytes = downloadedBytes,
            speedBytesPerSec = speedBytesPerSec,
            status = downloadStatus,
            errorMessage = errorMessage,
            platform = platformType,
            createdAt = createdAt,
            completedAt = completedAt
        )
    }

    companion object {
        fun fromDownloadItem(item: DownloadItem): DownloadEntity {
            return DownloadEntity(
                id = item.id,
                originalUrl = item.originalUrl,
                downloadUrl = item.downloadUrl,
                title = item.title,
                author = item.author,
                thumbnailUrl = item.thumbnailUrl,
                formatLabel = item.formatLabel,
                container = item.container,
                isAudioOnly = item.isAudioOnly,
                localFilePath = item.localFilePath,
                mediaStoreUri = item.mediaStoreUri,
                totalBytes = item.totalBytes,
                downloadedBytes = item.downloadedBytes,
                speedBytesPerSec = item.speedBytesPerSec,
                status = item.status.name,
                errorMessage = item.errorMessage,
                platform = item.platform.name,
                createdAt = item.createdAt,
                completedAt = item.completedAt
            )
        }
    }
}
