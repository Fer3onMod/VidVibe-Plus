package com.example.data.local

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore by preferencesDataStore(name = "settings")

class AppSettings(private val context: Context) {
    companion object {
        val IS_DARK_MODE = booleanPreferencesKey("is_dark_mode")
        val LANGUAGE = stringPreferencesKey("language")
        val DEFAULT_QUALITY = stringPreferencesKey("default_quality")
        val WIFI_ONLY = booleanPreferencesKey("wifi_only")
        val AUTO_PASTE = booleanPreferencesKey("auto_paste")
        val MAX_CONCURRENT = intPreferencesKey("max_concurrent")
        val NOTIFICATIONS_ENABLED = booleanPreferencesKey("notifications_enabled")
    }

    val isDarkModeFlow: Flow<Boolean?> = context.dataStore.data
        .map { preferences ->
            preferences[IS_DARK_MODE]
        }

    val languageFlow: Flow<String> = context.dataStore.data
        .map { preferences ->
            preferences[LANGUAGE] ?: "en"
        }

    val defaultQualityFlow: Flow<String> = context.dataStore.data
        .map { preferences ->
            preferences[DEFAULT_QUALITY] ?: "best"
        }

    val wifiOnlyFlow: Flow<Boolean> = context.dataStore.data
        .map { preferences ->
            preferences[WIFI_ONLY] ?: false
        }

    val autoPasteFlow: Flow<Boolean> = context.dataStore.data
        .map { preferences ->
            preferences[AUTO_PASTE] ?: true
        }

    val maxConcurrentFlow: Flow<Int> = context.dataStore.data
        .map { preferences ->
            preferences[MAX_CONCURRENT] ?: 3
        }

    val notificationsEnabledFlow: Flow<Boolean> = context.dataStore.data
        .map { preferences ->
            preferences[NOTIFICATIONS_ENABLED] ?: true
        }

    suspend fun setDarkMode(isDark: Boolean?) {
        context.dataStore.edit { settings ->
            if (isDark == null) {
                settings.remove(IS_DARK_MODE)
            } else {
                settings[IS_DARK_MODE] = isDark
            }
        }
    }

    suspend fun setLanguage(lang: String) {
        context.dataStore.edit { settings ->
            settings[LANGUAGE] = lang
        }
    }

    suspend fun setDefaultQuality(quality: String) {
        context.dataStore.edit { settings ->
            settings[DEFAULT_QUALITY] = quality
        }
    }

    suspend fun setWifiOnly(enabled: Boolean) {
        context.dataStore.edit { settings ->
            settings[WIFI_ONLY] = enabled
        }
    }

    suspend fun setAutoPaste(enabled: Boolean) {
        context.dataStore.edit { settings ->
            settings[AUTO_PASTE] = enabled
        }
    }

    suspend fun setMaxConcurrent(count: Int) {
        context.dataStore.edit { settings ->
            settings[MAX_CONCURRENT] = count
        }
    }

    suspend fun setNotificationsEnabled(enabled: Boolean) {
        context.dataStore.edit { settings ->
            settings[NOTIFICATIONS_ENABLED] = enabled
        }
    }
}
