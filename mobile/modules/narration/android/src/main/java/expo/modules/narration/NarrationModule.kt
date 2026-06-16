package expo.modules.narration

import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import expo.modules.kotlin.Promise
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class NarrationModule : Module() {
  private val mainHandler = Handler(Looper.getMainLooper())

  override fun definition() = ModuleDefinition {
    Name("Narration")

    Function("play") { id: String, url: String, title: String, artist: String ->
      val context = appContext.reactContext ?: return@Function false
      NarrationService.currentId = id
      val intent = Intent(context, NarrationService::class.java).apply {
        action = NarrationService.ACTION_PLAY
        putExtra(NarrationService.EXTRA_ID, id)
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

    Function("pausePlay") {
      mainHandler.post {
        NarrationService.instance?.mediaSession?.player?.let {
          it.playWhenReady = !it.playWhenReady
        }
      }
    }

    Function("seekToMs") { positionMs: Double ->
      mainHandler.post {
        NarrationService.instance?.mediaSession?.player?.seekTo(positionMs.toLong())
      }
    }

    Function("currentId") {
      NarrationService.currentId
    }

    AsyncFunction("getStatus") { promise: Promise ->
      mainHandler.post {
        val player = NarrationService.instance?.mediaSession?.player
        promise.resolve(
          mapOf(
            "id" to NarrationService.currentId,
            "playing" to (player?.isPlaying ?: false),
            "positionMs" to (player?.currentPosition ?: 0L).toDouble(),
            "durationMs" to (player?.duration?.takeIf { it > 0 } ?: 0L).toDouble()
          )
        )
      }
    }
  }
}
