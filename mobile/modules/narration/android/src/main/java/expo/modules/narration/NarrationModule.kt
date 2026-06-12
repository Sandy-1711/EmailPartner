package expo.modules.narration

import android.content.Intent
import android.os.Build
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class NarrationModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("Narration")

    Function("play") { id: String, url: String, title: String, artist: String ->
      val context = appContext.reactContext ?: return@Function false
      NarrationService.currentId = id
      val intent = Intent(context, NarrationService::class.java).apply {
        action = NarrationService.ACTION_PLAY
        putExtra(NarrationService.EXTRA_URL, url)
        putExtra(NarrationService.EXTRA_TITLE, title)
        putExtra(NarrationService.EXTRA_ARTIST, artist)
      }
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        context.startForegroundService(intent)
      } else {
        context.startService(intent)
      }
      true
    }

    Function("stop") {
      val context = appContext.reactContext ?: return@Function false
      NarrationService.currentId = null
      // delivering an intent to an already-running foreground service is allowed
      val intent = Intent(context, NarrationService::class.java).apply {
        action = NarrationService.ACTION_STOP
      }
      context.startService(intent)
      true
    }

    Function("currentId") {
      NarrationService.currentId
    }
  }
}
