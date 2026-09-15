package com.example.data.repository

import android.content.Context
import android.net.Uri
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.example.data.api.MediaLinkExtractor
import com.example.data.local.AppDatabase
import com.example.data.local.DownloadEntity
import com.example.data.model.DownloadItem
import com.example.data.model.DownloadStatus
import com.example.data.model.VideoFormat
import com.example.data.model.VideoMetadata
import com.example.worker.DownloadWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID

interface VideoRepository {
    suspend fun parseUrl(rawUrl: String): Result<List<VideoMetadata>>
    suspend fun startDownload(metadata: VideoMetadata, format: VideoFormat): String
    suspend fun pauseDownload(id: String)
    suspend fun resumeDownload(id: String)
    suspend fun cancelDownload(id: String)
    suspend fun deleteDownload(id: String, deleteFile: Boolean)
    suspend fun renameDownload(id: String, newTitle: String)
    fun getAllDownloads(): Flow<List<DownloadItem>>
    fun getActiveDownloads(): Flow<List<DownloadItem>>
    fun getCompletedDownloads(): Flow<List<DownloadItem>>
}

class VideoRepositoryImpl(
    private val context: Context,
    private val extractor: MediaLinkExtractor = MediaLinkExtractor(),
    private val database: AppDatabase = AppDatabase.getInstance(context)
) : VideoRepository {

    private val dao = database.downloadDao()
    private val workManager: WorkManager? by lazy {
        try {
            WorkManager.getInstance(context)
        } catch (e: Exception) {
            null
        }
    }

    override suspend fun parseUrl(rawUrl: String): Result<List<VideoMetadata>> {
        return extractor.extract(rawUrl)
    }

    override suspend fun startDownload(metadata: VideoMetadata, format: VideoFormat): String = withContext(Dispatchers.IO) {
        val downloadId = UUID.randomUUID().toString()

        val downloadItem = DownloadItem(
            id = downloadId,
            originalUrl = metadata.originalUrl,
            downloadUrl = format.directUrl,
            title = metadata.title,
            author = metadata.author,
            thumbnailUrl = metadata.thumbnailUrl,
            formatLabel = format.resolution,
            container = format.container,
            isAudioOnly = format.isAudioOnly,
            totalBytes = format.estimatedSizeBytes,
            downloadedBytes = 0,
            speedBytesPerSec = 0,
            status = DownloadStatus.QUEUED,
            platform = metadata.platform,
            createdAt = System.currentTimeMillis()
        )

        dao.insertOrUpdate(DownloadEntity.fromDownloadItem(downloadItem))

        enqueueDownloadWork(
            downloadId = downloadId,
            downloadUrl = format.directUrl,
            title = metadata.title,
            isAudio = format.isAudioOnly,
            container = format.container
        )

        return@withContext downloadId
    }

    private fun enqueueDownloadWork(
        downloadId: String,
        downloadUrl: String,
        title: String,
        isAudio: Boolean,
        container: String
    ) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val inputData = workDataOf(
            DownloadWorker.KEY_DOWNLOAD_ID to downloadId,
            DownloadWorker.KEY_DOWNLOAD_URL to downloadUrl,
            DownloadWorker.KEY_TITLE to title,
            DownloadWorker.KEY_IS_AUDIO to isAudio,
            DownloadWorker.KEY_CONTAINER to container
        )

        val workRequest = OneTimeWorkRequestBuilder<DownloadWorker>()
            .setConstraints(constraints)
            .setInputData(inputData)
            .addTag("download_$downloadId")
            .build()

        workManager?.enqueueUniqueWork(
            "download_$downloadId",
            ExistingWorkPolicy.REPLACE,
            workRequest
        )
    }

    override suspend fun pauseDownload(id: String) = withContext(Dispatchers.IO) {
        workManager?.cancelUniqueWork("download_$id")
        dao.updateStatus(id, DownloadStatus.PAUSED.name)
    }

    override suspend fun resumeDownload(id: String) = withContext(Dispatchers.IO) {
        val entity = dao.getDownloadById(id) ?: return@withContext
        dao.updateStatus(id, DownloadStatus.QUEUED.name)
        enqueueDownloadWork(
            downloadId = entity.id,
            downloadUrl = entity.downloadUrl,
            title = entity.title,
            isAudio = entity.isAudioOnly,
            container = entity.container
        )
    }

    override suspend fun cancelDownload(id: String) = withContext(Dispatchers.IO) {
        workManager?.cancelUniqueWork("download_$id")
        dao.updateStatus(id, DownloadStatus.CANCELLED.name)
    }

    override suspend fun deleteDownload(id: String, deleteFile: Boolean) = withContext(Dispatchers.IO) {
        workManager?.cancelUniqueWork("download_$id")
        val entity = dao.getDownloadById(id)
        if (deleteFile && entity != null) {
            try {
                if (!entity.mediaStoreUri.isNullOrBlank()) {
                    context.contentResolver.delete(Uri.parse(entity.mediaStoreUri), null, null)
                }
                if (!entity.localFilePath.isNullOrBlank()) {
                    val file = File(entity.localFilePath)
                    if (file.exists()) file.delete()
                }
            } catch (_: Exception) {}
        }
        dao.deleteById(id)
    }

    override suspend fun renameDownload(id: String, newTitle: String) = withContext(Dispatchers.IO) {
        if (newTitle.isNotBlank()) {
            dao.updateTitle(id, newTitle.trim())
        }
    }

    override fun getAllDownloads(): Flow<List<DownloadItem>> {
        return dao.getAllDownloads().map { list -> list.map { it.toDownloadItem() } }
    }

    override fun getActiveDownloads(): Flow<List<DownloadItem>> {
        return dao.getActiveDownloads().map { list -> list.map { it.toDownloadItem() } }
    }

    override fun getCompletedDownloads(): Flow<List<DownloadItem>> {
        return dao.getCompletedDownloads().map { list -> list.map { it.toDownloadItem() } }
    }
}
