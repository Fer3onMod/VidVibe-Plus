package com.example.data.api

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class CobaltRequest(
    @param:Json(name = "url") val url: String,
    @param:Json(name = "videoQuality") val videoQuality: String? = "1080",
    @param:Json(name = "audioFormat") val audioFormat: String? = "mp3",
    @param:Json(name = "downloadMode") val downloadMode: String? = "auto",
    @param:Json(name = "youtubeVideoCodec") val youtubeVideoCodec: String? = "h264",
    @param:Json(name = "filenameStyle") val filenameStyle: String? = "classic"
)

@JsonClass(generateAdapter = true)
data class CobaltPickerItem(
    @param:Json(name = "type") val type: String? = null,
    @param:Json(name = "url") val url: String? = null,
    @param:Json(name = "thumb") val thumb: String? = null
)

@JsonClass(generateAdapter = true)
data class CobaltResponse(
    @param:Json(name = "status") val status: String? = null,
    @param:Json(name = "url") val url: String? = null,
    @param:Json(name = "filename") val filename: String? = null,
    @param:Json(name = "picker") val picker: List<CobaltPickerItem>? = null,
    @param:Json(name = "audio") val audio: String? = null,
    @param:Json(name = "text") val text: String? = null
)
