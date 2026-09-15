package com.example

import android.Manifest
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatDelegate
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.core.os.LocaleListCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.data.local.AppSettings
import com.example.ui.MainViewModel
import com.example.ui.components.NeonBottomNavBar
import com.example.ui.dialogs.BatchDownloadDialog
import com.example.ui.dialogs.FormatSelectionSheet
import com.example.ui.downloads.DownloadManagerScreen
import com.example.ui.home.HomeScreen
import com.example.ui.settings.AboutAppScreen
import com.example.ui.settings.SettingsScreen
import com.example.ui.splash.SplashScreen
import com.example.ui.whatsapp.WhatsAppStatusSaverScreen
import android.content.res.Configuration
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import java.util.Locale
import com.example.ui.theme.MyApplicationTheme
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleSharedIntent(intent)

        setContent {
            val isDarkFlow by viewModel.isDarkMode.collectAsState()
            val langFlow by viewModel.language.collectAsState()
            var showSplash by rememberSaveable { mutableStateOf(true) }

            val isArabic = langFlow == "ar"
            val layoutDirection = if (isArabic) LayoutDirection.Rtl else LayoutDirection.Ltr

            LaunchedEffect(langFlow) {
                try {
                    val currentLocales = AppCompatDelegate.getApplicationLocales()
                    val targetLocale = LocaleListCompat.forLanguageTags(if (langFlow == "ar") "ar" else "en")
                    if (currentLocales != targetLocale) {
                        AppCompatDelegate.setApplicationLocales(targetLocale)
                    }
                } catch (_: Exception) {}
            }

            val useDarkTheme = isDarkFlow ?: isSystemInDarkTheme()

            CompositionLocalProvider(
                LocalLayoutDirection provides layoutDirection
            ) {
                MyApplicationTheme(darkTheme = useDarkTheme) {
                    if (showSplash) {
                        SplashScreen(
                            onSplashFinished = { showSplash = false }
                        )
                    } else {
                        MainApp(
                            viewModel = viewModel,
                            onGetClipboard = { readFromClipboard() }
                        )
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleSharedIntent(intent)
    }

    private fun handleSharedIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!sharedText.isNullOrBlank()) {
                val urlRegex = Regex("https?://\\S+")
                val match = urlRegex.find(sharedText)
                val targetUrl = match?.value ?: sharedText.trim()
                viewModel.pasteAndAnalyze(targetUrl)
            }
        }
    }

    private fun readFromClipboard(): String? {
        return try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clip = clipboard?.primaryClip
            if (clip != null && clip.itemCount > 0) {
                val item = clip.getItemAt(0)
                item.coerceToText(this)?.toString()?.trim()
            } else {
                null
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainApp(
    viewModel: MainViewModel,
    onGetClipboard: () -> String?,
    modifier: Modifier = Modifier
) {
    val navController = rememberNavController()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route ?: "home"

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    LaunchedEffect(Unit) {
        val permissionsToRequest = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissionsToRequest.add(Manifest.permission.POST_NOTIFICATIONS)
            permissionsToRequest.add(Manifest.permission.READ_MEDIA_VIDEO)
        } else {
            permissionsToRequest.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
        if (permissionsToRequest.isNotEmpty()) {
            permissionLauncher.launch(permissionsToRequest.toTypedArray())
        }
    }

    val autoPaste by viewModel.autoPaste.collectAsState()
    LaunchedEffect(Unit) {
        if (autoPaste && viewModel.urlInput.value.isBlank()) {
            val clip = onGetClipboard()
            if (!clip.isNullOrBlank()) {
                val urlRegex = Regex("https?://\\S+")
                val match = urlRegex.find(clip)
                if (match != null) {
                    viewModel.onUrlChanged(match.value)
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        viewModel.userMessage.collectLatest { message ->
            val result = snackbarHostState.showSnackbar(
                message = message,
                actionLabel = if (message.startsWith("Download started")) "View" else null,
                duration = SnackbarDuration.Short
            )
            if (result == SnackbarResult.ActionPerformed) {
                navController.navigate("downloads") {
                    popUpTo("home") { saveState = true }
                    launchSingleTop = true
                    restoreState = true
                }
            }
        }
    }

    val urlInput by viewModel.urlInput.collectAsState()
    val detectedPlatform by viewModel.detectedPlatform.collectAsState()
    val isAnalyzing by viewModel.isAnalyzing.collectAsState()
    val analysisError by viewModel.analysisError.collectAsState()
    val currentMetadata by viewModel.currentMetadata.collectAsState()
    val showFormatSheet by viewModel.showFormatSheet.collectAsState()
    val allDownloads by viewModel.allDownloads.collectAsState()
    val activeDownloads by viewModel.activeDownloads.collectAsState()
    val completedDownloads by viewModel.completedDownloads.collectAsState()
    val activeDownloadCount by viewModel.activeDownloadCount.collectAsState()
    val aiState by viewModel.aiState.collectAsState()

    // Settings states
    val isDarkMode by viewModel.isDarkMode.collectAsState()
    val language by viewModel.language.collectAsState()
    val wifiOnly by viewModel.wifiOnly.collectAsState()
    val maxConcurrent by viewModel.maxConcurrent.collectAsState()
    val notificationsEnabled by viewModel.notificationsEnabled.collectAsState()

    val showBatchDialog by viewModel.showBatchDialog.collectAsState()
    val currentBatchItems by viewModel.currentBatchItems.collectAsState()

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    Scaffold(
        modifier = modifier.fillMaxSize(),
        bottomBar = {
            NeonBottomNavBar(
                currentRoute = currentRoute,
                activeDownloadCount = activeDownloadCount,
                onNavigate = { route ->
                    navController.navigate(route) {
                        popUpTo("home") { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(innerPadding)
        ) {
            composable("home") {
                HomeScreen(
                    urlInput = urlInput,
                    detectedPlatform = detectedPlatform,
                    isAnalyzing = isAnalyzing,
                    errorMessage = analysisError,
                    activeDownloadCount = activeDownloadCount,
                    onUrlChange = { viewModel.onUrlChanged(it) },
                    onClearUrl = { viewModel.clearUrl() },
                    onPasteClick = {
                        val clip = onGetClipboard()
                        if (!clip.isNullOrBlank()) {
                            val urlRegex = Regex("https?://\\S+")
                            val match = urlRegex.find(clip)
                            val targetUrl = match?.value ?: clip.trim()
                            viewModel.onUrlChanged(targetUrl)
                            scope.launch {
                                snackbarHostState.showSnackbar("Pasted link from clipboard")
                            }
                        } else {
                            scope.launch {
                                snackbarHostState.showSnackbar("Clipboard is empty or contains no link")
                            }
                        }
                    },
                    onAnalyzeClick = { viewModel.analyzeUrl() },
                    onNavigateToDownloads = {
                        navController.navigate("downloads") {
                            popUpTo("home") { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onNavigateToWhatsAppSaver = { navController.navigate("whatsapp_status") },
                    onViewSupportedPlatforms = {
                        navController.navigate("about")
                    }
                )
            }
            composable("downloads") {
                DownloadManagerScreen(
                    allDownloads = allDownloads,
                    activeDownloads = activeDownloads,
                    completedDownloads = completedDownloads,
                    onBackClick = { navController.popBackStack() },
                    onPauseClick = { viewModel.pauseDownload(it) },
                    onResumeClick = { viewModel.resumeDownload(it) },
                    onCancelClick = { viewModel.cancelDownload(it) },
                    onDeleteClick = { viewModel.deleteDownload(it, deleteFile = true) },
                    onRenameClick = { id, newTitle -> viewModel.renameDownload(id, newTitle) }
                )
            }
            composable("whatsapp_status") {
                WhatsAppStatusSaverScreen(
                    onBackClick = { navController.popBackStack() }
                )
            }
            composable("settings") {
                SettingsScreen(
                    isDarkMode = isDarkMode,
                    currentLanguage = language,
                    wifiOnly = wifiOnly,
                    autoPaste = autoPaste,
                    maxConcurrent = maxConcurrent,
                    notificationsEnabled = notificationsEnabled,
                    onDarkModeChange = { viewModel.setDarkMode(it) },
                    onLanguageChange = { viewModel.setLanguage(it) },
                    onWifiOnlyChange = { viewModel.setWifiOnly(it) },
                    onAutoPasteChange = { viewModel.setAutoPaste(it) },
                    onMaxConcurrentChange = { viewModel.setMaxConcurrent(it) },
                    onNotificationsChange = { viewModel.setNotificationsEnabled(it) },
                    onNavigateToAbout = { navController.navigate("about") }
                )
            }
            composable("about") {
                AboutAppScreen(
                    onBackClick = { navController.popBackStack() }
                )
            }
        }

        if (showFormatSheet && currentMetadata != null) {
            FormatSelectionSheet(
                metadata = currentMetadata,
                sheetState = sheetState,
                aiState = aiState,
                onDismiss = { viewModel.dismissFormatSheet() },
                onDownloadFormat = { format ->
                    viewModel.startDownload(format)
                },
                onRunAiAnalysis = {
                    viewModel.runAiAnalysis()
                }
            )
        }

        if (showBatchDialog) {
            BatchDownloadDialog(
                items = currentBatchItems,
                onDismissRequest = { viewModel.dismissBatchDialog() },
                onStartBatch = { items, isAudio ->
                    viewModel.startMultiItemDownload(items, isAudio)
                }
            )
        }
    }
}
