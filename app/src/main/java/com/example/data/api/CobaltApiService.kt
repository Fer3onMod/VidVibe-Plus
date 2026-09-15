package com.example.data.api

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST
import retrofit2.http.Url

interface CobaltApiService {

    @Headers(
        "Accept: application/json",
        "Content-Type: application/json"
    )
    @POST
    suspend fun extractMedia(
        @Url endpointUrl: String,
        @Body request: CobaltRequest,
        @Header("Accept") acceptHeader: String = "application/json"
    ): Response<CobaltResponse>
}
