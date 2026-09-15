import re
with open("app/src/main/java/com/example/MainActivity.kt", "r") as f:
    content = f.read()

# Add imports
imports = """
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import com.example.data.local.AppSettings
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.foundation.isSystemInDarkTheme
import com.example.ui.dialogs.SettingsDialog
"""

content = content.replace("class MainActivity", imports + "\nclass MainActivity")

# Add appSettings to MainActivity
onCreate = """
    private lateinit var appSettings: AppSettings

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        appSettings = AppSettings(this)
"""
content = re.sub(r'override fun onCreate\([^\)]+\) \{[\s]+super\.onCreate\([^\)]+\)', onCreate, content)

# Load settings and set content
setContent = """
        setContent {
            val isDarkFlow by appSettings.isDarkModeFlow.collectAsState(initial = null)
            val langFlow by appSettings.languageFlow.collectAsState(initial = "en")
            
            LaunchedEffect(langFlow) {
                AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(langFlow))
            }
            
            val useDarkTheme = isDarkFlow ?: isSystemInDarkTheme()
            var showSettings by remember { mutableStateOf(false) }

            MyApplicationTheme(darkTheme = useDarkTheme) {
                MainApp(
                    viewModel = viewModel,
                    onGetClipboard = { readFromClipboard() },
                    onSettingsClick = { showSettings = true }
                )
                
                if (showSettings) {
                    SettingsDialog(
                        isDarkMode = isDarkFlow,
                        currentLanguage = langFlow,
                        onDarkModeChange = { scope ->
                            lifecycleScope.launch { appSettings.setDarkMode(it ?: false) } // Wait, need scope
                        },
                        onLanguageChange = { lang ->
                            lifecycleScope.launch { appSettings.setLanguage(lang) }
                        },
                        onDismiss = { showSettings = false }
                    )
                }
            }
        }
"""
# We'll just patch the setContent block using string manipulation
