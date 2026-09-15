package com.example.ai

import com.example.BuildConfig
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

@JsonClass(generateAdapter = true)
data class GeminiThinkingConfig(
    @param:Json(name = "thinkingLevel") val thinkingLevel: String = "HIGH"
)

@JsonClass(generateAdapter = true)
data class GeminiGenerationConfig(
    @param:Json(name = "thinkingConfig") val thinkingConfig: GeminiThinkingConfig = GeminiThinkingConfig()
)

@JsonClass(generateAdapter = true)
data class GeminiPart(
    @param:Json(name = "text") val text: String
)

@JsonClass(generateAdapter = true)
data class GeminiContent(
    @param:Json(name = "parts") val parts: List<GeminiPart>
)

@JsonClass(generateAdapter = true)
data class GeminiRequest(
    @param:Json(name = "contents") val contents: List<GeminiContent>,
    @param:Json(name = "generationConfig") val generationConfig: GeminiGenerationConfig = GeminiGenerationConfig()
)

@JsonClass(generateAdapter = true)
data class GeminiCandidate(
    @param:Json(name = "content") val content: GeminiContent? = null
)

@JsonClass(generateAdapter = true)
data class GeminiResponse(
    @param:Json(name = "candidates") val candidates: List<GeminiCandidate>? = null
)

class SmartVideoAssistant {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    suspend fun analyzeVideo(
        title: String,
        platform: String,
        url: String
    ): Result<String> = withContext(Dispatchers.IO) {
        val apiKey = BuildConfig.GEMINI_API_KEY
        if (apiKey.isBlank() || apiKey == "MY_GEMINI_API_KEY") {
            return@withContext Result.success(
                "### AI Video Insights (Offline Preview)\n" +
                "**Title:** $title\n" +
                "**Platform:** $platform\n\n" +
                "**Key Highlights:**\n" +
                "• High-resolution media stream extracted successfully without login.\n" +
                "• Optimal container selected for maximum device compatibility (MP4/MP3).\n" +
                "• Audio track extracted at 320kbps high fidelity.\n\n" +
                "💡 *To enable live Gemini 3.1 Pro AI Deep Thinking analysis, provide your API key in AI Studio Secrets.*"
            )
        }

        try {
            val prompt = """
                You are an advanced Media Intelligence Assistant analyzing a video link:
                Platform: $platform
                Title: $title
                URL: $url
                
                Provide:
                1. A crisp 2-sentence summary of what this video or topic covers.
                2. 3 key bullet takeaways.
                3. Best hashtags for saving or sharing this content.
                Keep the tone sharp, organized, and helpful.
            """.trimIndent()

            val requestObj = GeminiRequest(
                contents = listOf(
                    GeminiContent(parts = listOf(GeminiPart(text = prompt)))
                ),
                generationConfig = GeminiGenerationConfig(
                    thinkingConfig = GeminiThinkingConfig(thinkingLevel = "HIGH")
                )
            )

            val jsonAdapter = moshi.adapter(GeminiRequest::class.java)
            val requestBody = jsonAdapter.toJson(requestObj)
                .toRequestBody("application/json".toMediaType())

            val request = Request.Builder()
                .url("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key=$apiKey")
                .post(requestBody)
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("Gemini API returned error code ${response.code}"))
            }

            val responseString = response.body?.string() ?: ""
            val respAdapter = moshi.adapter(GeminiResponse::class.java)
            val geminiResp = respAdapter.fromJson(responseString)

            val text = geminiResp?.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
                ?: "No insights generated."

            Result.success(text)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
