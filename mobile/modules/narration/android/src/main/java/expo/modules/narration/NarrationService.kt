package expo.modules.narration

import android.content.Intent
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService

/**
 * Singleton narration playback for Echo Mail.
 *
 * One foreground MediaSessionService owns one ExoPlayer for widget-initiated
 * narration: started directly from the widget tap (inside Android's
 * background-FGS allowance window), so playback gets lock-screen controls
 * and stop always works — no JS context or player handle required.
 */
class NarrationService : MediaSessionService() {
  var mediaSession: MediaSession? = null
    private set

  override fun onCreate() {
    super.onCreate()
    instance = this
    val player = ExoPlayer.Builder(this).build()
    player.addListener(object : Player.Listener {
      override fun onPlaybackStateChanged(playbackState: Int) {
        if (playbackState == Player.STATE_ENDED) {
          stopPlayback()
        }
      }
    })
    mediaSession = MediaSession.Builder(this, player).build()
  }

  override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? =
    mediaSession

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    when (intent?.action) {
      ACTION_PLAY -> {
        val url = intent.getStringExtra(EXTRA_URL)
        val player = mediaSession?.player
        if (url != null && player != null) {
          val item = MediaItem.Builder()
            .setUri(url)
            .setMediaMetadata(
              MediaMetadata.Builder()
                .setTitle(intent.getStringExtra(EXTRA_TITLE) ?: "Email summary")
                .setArtist(intent.getStringExtra(EXTRA_ARTIST) ?: "")
                .setAlbumTitle("Echo Mail")
                .build()
            )
            .build()
          player.setMediaItem(item)
          player.prepare()
          player.play()
        }
      }
      ACTION_STOP -> stopPlayback()
    }
    super.onStartCommand(intent, flags, startId)
    return START_NOT_STICKY
  }

  private fun stopPlayback() {
    currentId = null
    mediaSession?.player?.stop()
    stopSelf()
  }

  override fun onTaskRemoved(rootIntent: Intent?) {
    stopPlayback()
  }

  override fun onDestroy() {
    currentId = null
    instance = null
    mediaSession?.run {
      player.release()
      release()
    }
    mediaSession = null
    super.onDestroy()
  }

  companion object {
    const val ACTION_PLAY = "expo.modules.narration.PLAY"
    const val ACTION_STOP = "expo.modules.narration.STOP"
    const val EXTRA_URL = "url"
    const val EXTRA_TITLE = "title"
    const val EXTRA_ARTIST = "artist"

    /** Card id currently playing; process-wide, survives JS context teardown. */
    @Volatile
    var currentId: String? = null

    /** Live service instance for main-thread player access from the module. */
    @Volatile
    var instance: NarrationService? = null
  }
}
