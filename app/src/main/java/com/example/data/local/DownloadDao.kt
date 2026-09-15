package com.example.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface DownloadDao {
    @Query("SELECT * FROM downloads ORDER BY createdAt DESC")
    fun getAllDownloads(): Flow<List<DownloadEntity>>

    @Query("SELECT * FROM downloads WHERE status IN ('QUEUED', 'DOWNLOADING') ORDER BY createdAt DESC")
    fun getActiveDownloads(): Flow<List<DownloadEntity>>

    @Query("SELECT * FROM downloads WHERE status = 'COMPLETED' ORDER BY completedAt DESC")
    fun getCompletedDownloads(): Flow<List<DownloadEntity>>

    @Query("SELECT * FROM downloads WHERE id = :id LIMIT 1")
    suspend fun getDownloadById(id: String): DownloadEntity?

    @Query("SELECT * FROM downloads WHERE id = :id LIMIT 1")
    fun observeDownloadById(id: String): Flow<DownloadEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(download: DownloadEntity)

    @Update
    suspend fun update(download: DownloadEntity)

    @Query("""
        UPDATE downloads 
        SET downloadedBytes = :downloaded, totalBytes = :total, speedBytesPerSec = :speed, status = :status 
        WHERE id = :id
    """)
    suspend fun updateProgress(id: String, downloaded: Long, total: Long, speed: Long, status: String)

    @Query("UPDATE downloads SET status = :status WHERE id = :id")
    suspend fun updateStatus(id: String, status: String)

    @Query("UPDATE downloads SET title = :newTitle WHERE id = :id")
    suspend fun updateTitle(id: String, newTitle: String)

    @Query("""
        UPDATE downloads 
        SET status = 'COMPLETED', localFilePath = :filePath, mediaStoreUri = :mediaUri, completedAt = :completedAt, downloadedBytes = totalBytes, speedBytesPerSec = 0 
        WHERE id = :id
    """)
    suspend fun markCompleted(id: String, filePath: String, mediaUri: String, completedAt: Long)

    @Query("UPDATE downloads SET status = 'FAILED', errorMessage = :error, speedBytesPerSec = 0 WHERE id = :id")
    suspend fun markFailed(id: String, error: String)

    @Query("DELETE FROM downloads WHERE id = :id")
    suspend fun deleteById(id: String)

    @Query("DELETE FROM downloads")
    suspend fun clearAll()
}
