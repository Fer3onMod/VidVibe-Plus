package com.example.data.api

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response
import okio.Buffer

class NetworkDebugger : Interceptor {
    private val TAG = "NetworkDebugger"

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()

        Log.d(TAG, "========== NETWORK REQUEST ==========")
        Log.d(TAG, "URL: ${request.url}")
        Log.d(TAG, "Method: ${request.method}")
        Log.d(TAG, "Headers: \n${request.headers}")
        
        request.body?.let { body ->
            val buffer = Buffer()
            body.writeTo(buffer)
            Log.d(TAG, "Request Body: ${buffer.readUtf8()}")
        }

        val response = try {
            chain.proceed(request)
        } catch (e: Exception) {
            Log.e(TAG, "Network request failed: ${e.message}", e)
            throw e
        }

        Log.d(TAG, "========== NETWORK RESPONSE =========")
        Log.d(TAG, "URL: ${response.request.url}")
        Log.d(TAG, "Code: ${response.code}")
        Log.d(TAG, "Message: ${response.message}")
        Log.d(TAG, "Headers: \n${response.headers}")

        val responseBody = response.body
        if (responseBody != null) {
            try {
                val source = responseBody.source()
                source.request(Long.MAX_VALUE) // Buffer the entire body
                val buffer = source.buffer
                Log.d(TAG, "Response Body: \n${buffer.clone().readUtf8()}")
            } catch (e: Exception) {
                Log.e(TAG, "Could not read response body: ${e.message}")
            }
        }

        Log.d(TAG, "=====================================")

        return response
    }
}
