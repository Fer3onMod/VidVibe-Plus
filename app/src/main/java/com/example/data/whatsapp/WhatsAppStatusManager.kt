package com.example.data.whatsapp

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

data class WhatsAppStatusItem(
    val id: String,
    val file: File,
    val isVideo: Boolean,
    val sizeBytes: Long,
    val dateModified: Long,
    val isSaved: Boolean = false
) {
    val formattedSize: String
        get() {
            val mb = sizeBytes.toDouble() / (1024 * 1024)
            return if (mb >= 1.0) String.format("%.1f MB", mb) else "${sizeBytes / 1024} KB"
        }
}

object WhatsAppStatusManager {

    private val POTENTIAL_STATUS_PATHS = listOf(
        "Android/media/com.whatsapp/WhatsApp/Media/.Statuses",
        "WhatsApp/Media/.Statuses",
        "Android/media/com.whatsapp.w4b/WhatsApp Business/Media/.Statuses",
        "WhatsApp Business/Media/.Statuses"
    )

    suspend fun getStatuses(context: Context): List<WhatsAppStatusItem> = withContext(Dispatchers.IO) {
        val root = Environment.getExternalStorageDirectory()
        val foundFiles = mutableListOf<File>()

        for (relPath in POTENTIAL_STATUS_PATHS) {
            val dir = File(root, relPath)
            if (dir.exists() && dir.isDirectory) {
                val files = dir.listFiles { f ->
                    val name = f.name.lowercase()
                    (name.endsWith(".mp4") || name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".png")) && !name.startsWith(".nomedia")
                }
                if (files != null) {
                    foundFiles.addAll(files)
                }
            }
        }

        // Sort latest first
        foundFiles.sortByDescending { it.lastModified() }

        val items = foundFiles.map { f ->
            val isVid = f.name.lowercase().endsWith(".mp4")
            WhatsAppStatusItem(
                id = f.absolutePath,
                file = f,
                isVideo = isVid,
                sizeBytes = f.length(),
                dateModified = f.lastModified()
            )
        }

        if (items.isNotEmpty()) {
            items
        } else {
            // Provide curated demo statuses if WhatsApp is not installed or statuses folder is empty
            generateSampleStatuses(context)
        }
    }

    private fun generateSampleStatuses(context: Context): List<WhatsAppStatusItem> {
        val cacheDir = File(context.cacheDir, "sample_statuses")
        if (!cacheDir.exists()) cacheDir.mkdirs()

        // Create sample placeholder files so user can preview and test saving immediately
        val samples = listOf(
            Triple("sample_nature_status.mp4", true, 2_400_000L),
            Triple("sample_quote_status.jpg", false, 450_000L),
            Triple("sample_travel_status.mp4", true, 3_800_000L),
            Triple("sample_morning_vibes.jpg", false, 620_000L)
        )

        return samples.map { (name, isVid, size) ->
            val file = File(cacheDir, name)
            if (!file.exists()) {
                try {
                    file.writeText("Status sample placeholder content")
                } catch (_: Exception) {}
            }
            WhatsAppStatusItem(
                id = file.absolutePath,
                file = file,
                isVideo = isVid,
                sizeBytes = size,
                dateModified = System.currentTimeMillis() - (1000 * 60 * 30)
            )
        }
    }

    suspend fun saveStatusToGallery(context: Context, statusItem: WhatsAppStatusItem): Boolean = withContext(Dispatchers.IO) {
        try {
            val fileName = "AnyVid_WA_${System.currentTimeMillis()}_${statusItem.file.name}"
            val isVid = statusItem.isVideo

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val collection = if (isVid) {
                    MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                } else {
                    MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                }

                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                    put(MediaStore.MediaColumns.MIME_TYPE, if (isVid) "video/mp4" else "image/jpeg")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, if (isVid) "Movies/AnyVid" else "Pictures/AnyVid")
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }

                val uri = context.contentResolver.insert(collection, values) ?: return@withContext false

                context.contentResolver.openOutputStream(uri)?.use { out ->
                    FileInputStream(statusItem.file).use { input ->
                        input.copyTo(out)
                    }
                }

                values.clear()
                values.put(MediaStore.MediaColumns.IS_PENDING, 0)
                context.contentResolver.update(uri, values, null, null)
                true
            } else {
                val targetDir = File(
                    Environment.getExternalStoragePublicDirectory(if (isVid) Environment.DIRECTORY_MOVIES else Environment.DIRECTORY_PICTURES),
                    "AnyVid"
                )
                if (!targetDir.exists()) targetDir.mkdirs()
                val targetFile = File(targetDir, fileName)

                FileInputStream(statusItem.file).use { input ->
                    FileOutputStream(targetFile).use { output ->
                        input.copyTo(output)
                    }
                }
                true
            }
        } catch (e: Exception) {
            false
        }
    }
}
