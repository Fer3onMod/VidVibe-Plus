package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.data.model.PlatformType
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ExampleRobolectricTest {

  @Test
  fun `read string from context`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val appName = context.getString(R.string.app_name)
    assertEquals("Video Downloader", appName)
  }

  @Test
  fun `detect platform types accurately`() {
    assertEquals(PlatformType.YOUTUBE, PlatformType.detect("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
    assertEquals(PlatformType.YOUTUBE_SHORTS, PlatformType.detect("https://youtube.com/shorts/abc123xyz"))
    assertEquals(PlatformType.INSTAGRAM, PlatformType.detect("https://www.instagram.com/reel/C123456789/"))
    assertEquals(PlatformType.TIKTOK, PlatformType.detect("https://www.tiktok.com/@user/video/1234567890"))
    assertEquals(PlatformType.TWITTER_X, PlatformType.detect("https://twitter.com/user/status/123456789"))
    assertEquals(PlatformType.FACEBOOK, PlatformType.detect("https://www.facebook.com/watch/?v=123456"))
  }

  @Test
  fun `create MainViewModel via AndroidViewModelFactory successfully`() {
    val app = ApplicationProvider.getApplicationContext<android.app.Application>()
    val factory = androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(app)
    val viewModel = factory.create(com.example.ui.MainViewModel::class.java)
    org.junit.Assert.assertNotNull(viewModel)
  }

  @Test
  fun `extract url from text and update ViewModel`() {
    val app = ApplicationProvider.getApplicationContext<android.app.Application>()
    val viewModel = com.example.ui.MainViewModel(app)
    val copiedText = "Check out this reel https://www.instagram.com/reel/C123456789/ from Instagram!"
    val urlRegex = Regex("https?://\\S+")
    val match = urlRegex.find(copiedText)
    val targetUrl = match?.value ?: copiedText.trim()
    viewModel.onUrlChanged(targetUrl)
    assertEquals("https://www.instagram.com/reel/C123456789/", viewModel.urlInput.value)
    assertEquals(PlatformType.INSTAGRAM, viewModel.detectedPlatform.value)
  }
}
