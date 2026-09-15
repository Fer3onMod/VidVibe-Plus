package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.ai.SmartVideoAssistant
import com.example.data.local.AppSettings
import com.example.data.model.DownloadItem
import com.example.data.model.PlatformType
import com.example.data.model.VideoFormat
import com.example.data.model.VideoMetadata
import com.example.data.repository.VideoRepository
import com.example.data.repository.VideoRepositoryImpl
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed interface AiAnalysisState {
    object Idle : AiAnalysisState
    object Loading : AiAnalysisState
    data class Success(val insights: String) : AiAnalysisState
    data class Error(val message: String) : AiAnalysisState
}

class MainViewModel @JvmOverloads constructor(
    application: Application,
    private val repository: VideoRepository = VideoRepositoryImpl(application),
    private val aiAssistant: SmartVideoAssistant = SmartVideoAssistant(),
    val appSettings: AppSettings = AppSettings(application)
) : AndroidViewModel(application) {

    val isDarkMode: StateFlow<Boolean?> = appSettings.isDarkModeFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val language: StateFlow<String> = appSettings.languageFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), "en")

    val defaultQuality: StateFlow<String> = appSettings.defaultQualityFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), "best")

    val wifiOnly: StateFlow<Boolean> = appSettings.wifiOnlyFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), false)

    val autoPaste: StateFlow<Boolean> = appSettings.autoPasteFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), true)

    val maxConcurrent: StateFlow<Int> = appSettings.maxConcurrentFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 3)

    val notificationsEnabled: StateFlow<Boolean> = appSettings.notificationsEnabledFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), true)

    fun setDarkMode(isDark: Boolean?) {
        viewModelScope.launch { appSettings.setDarkMode(isDark) }
    }

    fun setLanguage(lang: String) {
        viewModelScope.launch { appSettings.setLanguage(lang) }
    }

    fun setDefaultQuality(quality: String) {
        viewModelScope.launch { appSettings.setDefaultQuality(quality) }
    }

    fun setWifiOnly(enabled: Boolean) {
        viewModelScope.launch { appSettings.setWifiOnly(enabled) }
    }

    fun setAutoPaste(enabled: Boolean) {
        viewModelScope.launch { appSettings.setAutoPaste(enabled) }
    }

    fun setMaxConcurrent(count: Int) {
        viewModelScope.launch { appSettings.setMaxConcurrent(count) }
    }

    fun setNotificationsEnabled(enabled: Boolean) {
        viewModelScope.launch { appSettings.setNotificationsEnabled(enabled) }
    }

    private val _urlInput = MutableStateFlow("")
    val urlInput: StateFlow<String> = _urlInput.asStateFlow()

    private val _detectedPlatform = MutableStateFlow(PlatformType.UNIVERSAL)
    val detectedPlatform: StateFlow<PlatformType> = _detectedPlatform.asStateFlow()

    private val _isAnalyzing = MutableStateFlow(false)
    val isAnalyzing: StateFlow<Boolean> = _isAnalyzing.asStateFlow()

    private val _analysisError = MutableStateFlow<String?>(null)
    val analysisError: StateFlow<String?> = _analysisError.asStateFlow()

    private val _currentMetadata = MutableStateFlow<VideoMetadata?>(null)
    val currentMetadata: StateFlow<VideoMetadata?> = _currentMetadata.asStateFlow()

    private val _currentBatchItems = MutableStateFlow<List<VideoMetadata>>(emptyList())
    val currentBatchItems: StateFlow<List<VideoMetadata>> = _currentBatchItems.asStateFlow()

    private val _showBatchDialog = MutableStateFlow(false)
    val showBatchDialog: StateFlow<Boolean> = _showBatchDialog.asStateFlow()

    private val _showFormatSheet = MutableStateFlow(false)
    val showFormatSheet: StateFlow<Boolean> = _showFormatSheet.asStateFlow()

    private val _userMessage = MutableSharedFlow<String>()
    val userMessage: SharedFlow<String> = _userMessage.asSharedFlow()

    private val _aiState = MutableStateFlow<AiAnalysisState>(AiAnalysisState.Idle)
    val aiState: StateFlow<AiAnalysisState> = _aiState.asStateFlow()

    val allDownloads: StateFlow<List<DownloadItem>> = repository.getAllDownloads()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val activeDownloads: StateFlow<List<DownloadItem>> = repository.getActiveDownloads()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val completedDownloads: StateFlow<List<DownloadItem>> = repository.getCompletedDownloads()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val activeDownloadCount: StateFlow<Int> = activeDownloads
        .map { it.size }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    fun onUrlChanged(newUrl: String) {
        _urlInput.value = newUrl
        _analysisError.value = null
        if (newUrl.isNotBlank()) {
            _detectedPlatform.value = PlatformType.detect(newUrl)
        } else {
            _detectedPlatform.value = PlatformType.UNIVERSAL
        }
    }

    fun clearUrl() {
        _urlInput.value = ""
        _detectedPlatform.value = PlatformType.UNIVERSAL
        _analysisError.value = null
    }

    fun pasteAndAnalyze(pastedUrl: String) {
        onUrlChanged(pastedUrl)
        analyzeUrl()
    }

    fun analyzeUrl() {
        val url = _urlInput.value.trim()
        if (url.isBlank()) {
            _analysisError.value = "Please paste or enter a video URL"
            return
        }

        viewModelScope.launch {
            _isAnalyzing.value = true
            _analysisError.value = null

            val result = repository.parseUrl(url)
            result.onSuccess { metadataList ->
                if (metadataList.isEmpty()) {
                    _analysisError.value = "No media found in the provided URL."
                } else if (metadataList.size == 1) {
                    _currentMetadata.value = metadataList.first()
                    _showFormatSheet.value = true
                } else {
                    _currentBatchItems.value = metadataList
                    _showBatchDialog.value = true
                }
                _aiState.value = AiAnalysisState.Idle
            }.onFailure { error ->
                _analysisError.value = error.localizedMessage ?: "Failed to parse video. Check your URL."
            }

            _isAnalyzing.value = false
        }
    }

    fun dismissFormatSheet() {
        _showFormatSheet.value = false
    }

    fun startDownload(format: VideoFormat) {
        val meta = _currentMetadata.value ?: return
        viewModelScope.launch {
            repository.startDownload(meta, format)
            _showFormatSheet.value = false
            _userMessage.emit("Download started for ${format.resolution}")
        }
    }

    fun pauseDownload(id: String) {
        viewModelScope.launch {
            repository.pauseDownload(id)
            _userMessage.emit("Download paused")
        }
    }

    fun resumeDownload(id: String) {
        viewModelScope.launch {
            repository.resumeDownload(id)
            _userMessage.emit("Resuming download...")
        }
    }

    fun cancelDownload(id: String) {
        viewModelScope.launch {
            repository.cancelDownload(id)
            _userMessage.emit("Download cancelled")
        }
    }

    fun deleteDownload(id: String, deleteFile: Boolean = true) {
        viewModelScope.launch {
            repository.deleteDownload(id, deleteFile)
            _userMessage.emit("Download removed")
        }
    }

    fun renameDownload(id: String, newTitle: String) {
        viewModelScope.launch {
            repository.renameDownload(id, newTitle)
            _userMessage.emit("File renamed successfully")
        }
    }

    fun dismissBatchDialog() {
        _showBatchDialog.value = false
        _currentBatchItems.value = emptyList()
    }

    fun startMultiItemDownload(items: List<VideoMetadata>, isAudioOnly: Boolean) {
        viewModelScope.launch {
            var enqueued = 0
            for (metadata in items) {
                val chosenFormat = if (isAudioOnly) {
                    metadata.availableFormats.find { it.isAudioOnly } ?: metadata.availableFormats.firstOrNull()
                } else {
                    metadata.availableFormats.find { !it.isAudioOnly } ?: metadata.availableFormats.firstOrNull()
                }
                if (chosenFormat != null) {
                    repository.startDownload(metadata, chosenFormat)
                    enqueued++
                }
            }
            if (enqueued > 0) {
                _userMessage.emit("Download started: $enqueued items queued")
            }
            dismissBatchDialog()
        }
    }

    fun runAiAnalysis() {
        val meta = _currentMetadata.value ?: return
        viewModelScope.launch {
            _aiState.value = AiAnalysisState.Loading
            val result = aiAssistant.analyzeVideo(
                title = meta.title,
                platform = meta.platform.displayName,
                url = meta.originalUrl
            )
            result.onSuccess { text ->
                _aiState.value = AiAnalysisState.Success(text)
            }.onFailure { err ->
                _aiState.value = AiAnalysisState.Error(err.message ?: "Failed to generate AI insights.")
            }
        }
    }

    fun clearAiState() {
        _aiState.value = AiAnalysisState.Idle
    }
}
