package com.example.worker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ContentValues
import android.content.Context
import android.content.pm.ServiceInfo
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ForegroundInfo
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.example.R
import com.example.data.local.AppDatabase
import com.example.data.model.DownloadStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.util.concurrent.TimeUnit

class DownloadWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val notificationManager =
        context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    companion object {
        const val CHANNEL_ID = "video_downloader_channel"
        const val KEY_DOWNLOAD_ID = "key_download_id"
        const val KEY_DOWNLOAD_URL = "key_download_url"
        const val KEY_TITLE = "key_title"
        const val KEY_IS_AUDIO = "key_is_audio"
        const val KEY_CONTAINER = "key_container"
        const val KEY_PROGRESS = "key_progress"
        const val KEY_SPEED = "key_speed"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val downloadId = inputData.getString(KEY_DOWNLOAD_ID) ?: return@withContext Result.failure()
        val downloadUrl = inputData.getString(KEY_DOWNLOAD_URL) ?: return@withContext Result.failure()
        val rawTitle = inputData.getString(KEY_TITLE) ?: "Downloaded_Media"
        val isAudio = inputData.getBoolean(KEY_IS_AUDIO, false)
        val container = inputData.getString(KEY_CONTAINER) ?: if (isAudio) "mp3" else "mp4"

        // Sanitize file title
        val cleanTitle = rawTitle.replace(Regex("[^a-zA-Z0-9._\\-\\s]"), "_").take(60).trim()
        val fileName = "${cleanTitle}_${System.currentTimeMillis()}.$container"

        val db = AppDatabase.getInstance(context)
        val dao = db.downloadDao()

        createNotificationChannel()

        val notificationId = downloadId.hashCode()
        setForeground(createForegroundInfo(cleanTitle, 0, "--", notificationId))

        dao.updateStatus(downloadId, DownloadStatus.DOWNLOADING.name)

        var outputStream: OutputStream? = null
        var inputStream: InputStream? = null
        var mediaStoreUri: Uri? = null
        var savedFile: File? = null

        try {
            val request = Request.Builder()
                .url(downloadUrl)
                .header("User-Agent", "Mozilla/5.0 (Android; UniversalDownloader/1.0)")
                .build()

            val response = okHttpClient.newCall(request).execute()
            if (!response.isSuccessful) {
                dao.markFailed(downloadId, "HTTP error: ${response.code}")
                return@withContext Result.failure()
            }

            val body = response.body ?: run {
                dao.markFailed(downloadId, "Empty response body")
                return@withContext Result.failure()
            }

            val contentLength = body.contentLength().let { if (it > 0) it else 35_000_000L }
            inputStream = body.byteStream()

            // Setup output destination via MediaStore or public file storage
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val collection = if (isAudio) {
                    MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                } else {
                    MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                }

                val mimeType = if (isAudio) "audio/mpeg" else "video/mp4"
                val relativePath = if (isAudio) {
                    "${Environment.DIRECTORY_MUSIC}/VideoDownloader"
                } else {
                    "${Environment.DIRECTORY_MOVIES}/VideoDownloader"
                }

                val contentValues = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                    put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }

                val uri = context.contentResolver.insert(collection, contentValues)
                    ?: throw IllegalStateException("Failed to create MediaStore entry")
                mediaStoreUri = uri
                outputStream = context.contentResolver.openOutputStream(uri)
            } else {
                @Suppress("DEPRECATION")
                val publicDir = if (isAudio) {
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC)
                } else {
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES)
                }
                val appFolder = File(publicDir, "VideoDownloader").apply { mkdirs() }
                val target = File(appFolder, fileName)
                savedFile = target
                outputStream = FileOutputStream(target)
            }

            val buffer = ByteArray(16 * 1024)
            var bytesRead: Int
            var totalBytesRead = 0L
            var lastUpdateTime = System.currentTimeMillis()
            var bytesSinceLastUpdate = 0L
            var currentSpeed = 0L

            while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                if (isStopped) {
                    dao.updateStatus(downloadId, DownloadStatus.PAUSED.name)
                    return@withContext Result.retry()
                }

                outputStream?.write(buffer, 0, bytesRead)
                totalBytesRead += bytesRead
                bytesSinceLastUpdate += bytesRead

                val now = System.currentTimeMillis()
                val delta = now - lastUpdateTime
                if (delta >= 500) {
                    currentSpeed = (bytesSinceLastUpdate * 1000) / delta
                    lastUpdateTime = now
                    bytesSinceLastUpdate = 0

                    val progress = ((totalBytesRead.toDouble() / contentLength.toDouble()) * 100)
                        .toInt().coerceIn(0, 99)

                    // Update WorkManager progress for any attached observers
                    setProgress(
                        workDataOf(
                            KEY_PROGRESS to progress,
                            KEY_SPEED to currentSpeed
                        )
                    )

                    // Update Room database
                    dao.updateProgress(
                        id = downloadId,
                        downloaded = totalBytesRead,
                        total = contentLength,
                        speed = currentSpeed,
                        status = DownloadStatus.DOWNLOADING.name
                    )

                    val speedStr = formatSpeed(currentSpeed)
                    notificationManager.notify(
                        notificationId,
                        buildProgressNotification(cleanTitle, progress, speedStr)
                    )
                }
            }

            outputStream?.flush()

            // Finalize MediaStore entry by clearing IS_PENDING
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && mediaStoreUri != null) {
                val finalizeValues = ContentValues().apply {
                    put(MediaStore.MediaColumns.IS_PENDING, 0)
                }
                context.contentResolver.update(mediaStoreUri, finalizeValues, null, null)
            }

            val finalPath = savedFile?.absolutePath ?: mediaStoreUri?.toString() ?: ""
            dao.markCompleted(
                id = downloadId,
                filePath = finalPath,
                mediaUri = mediaStoreUri?.toString() ?: "",
                completedAt = System.currentTimeMillis()
            )

            // Complete Notification
            showCompletedNotification(cleanTitle, notificationId)

            Result.success()
        } catch (e: Exception) {
            if (isStopped) {
                dao.updateStatus(downloadId, DownloadStatus.CANCELLED.name)
                Result.failure()
            } else {
                dao.markFailed(downloadId, e.message ?: "Download failed")
                Result.failure()
            }
        } finally {
            try {
                inputStream?.close()
                outputStream?.close()
            } catch (_: Exception) {}
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Video Downloads",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows real-time download progress for videos and audio"
                enableVibration(false)
            }
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createForegroundInfo(
        title: String,
        progress: Int,
        speed: String,
        notificationId: Int
    ): ForegroundInfo {
        val notification = buildProgressNotification(title, progress, speed)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ForegroundInfo(
                notificationId,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            ForegroundInfo(notificationId, notification)
        }
    }

    private fun buildProgressNotification(title: String, progress: Int, speed: String) =
        NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("Downloading $title")
            .setContentText("$progress% • $speed")
            .setSmallIcon(R.drawable.app_icon_fg)
            .setProgress(100, progress, false)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .build()

    private fun showCompletedNotification(title: String, notificationId: Int) {
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("Download Finished")
            .setContentText("$title saved to Gallery")
            .setSmallIcon(R.drawable.app_icon_fg)
            .setAutoCancel(true)
            .build()
        notificationManager.notify(notificationId, notification)
    }

    private fun formatSpeed(bytesPerSec: Long): String {
        if (bytesPerSec <= 0) return "--"
        val kb = bytesPerSec / 1024.0
        val mb = kb / 1024.0
        return if (mb >= 1.0) {
            String.format("%.1f MB/s", mb)
        } else {
            String.format("%.0f KB/s", kb)
        }
    }
}
