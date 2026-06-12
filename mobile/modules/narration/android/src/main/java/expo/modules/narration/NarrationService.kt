package expo.modules.narration

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
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

  /**
   * startForegroundService() demands startForeground() within 5s, but media3
   * only promotes once playback is "ongoing" — a fast play->stop toggle kills
   * the whole app (ForegroundServiceDidNotStartInTimeException). So we post a
   * minimal notification immediately; media3 replaces it with the media one.
   */
  private fun ensureForeground() {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val manager = getSystemService(NotificationManager::class.java)
      if (manager.getNotificationChannel(CHANNEL_ID) == null) {
        manager.createNotificationChannel(
          NotificationChannel(CHANNEL_ID, "Narration", NotificationManager.IMPORTANCE_LOW)
        )
      }
    }
    val notification = NotificationCompat.Builder(this, CHANNEL_ID)
      .setSmallIcon(android.R.drawable.ic_media_play)
      .setContentTitle("Echo Mail")
      .setContentText("Narration")
      .setOngoing(true)
      .build()
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
      startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
    } else {
      startForeground(NOTIFICATION_ID, notification)
    }
  }

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    ensureForeground()
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
    stopForeground(STOP_FOREGROUND_REMOVE)
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
    const val CHANNEL_ID = "narration"
    const val NOTIFICATION_ID = 1001

    /** Card id currently playing; process-wide, survives JS context teardown. */
    @Volatile
    var currentId: String? = null

    /** Live service instance for main-thread player access from the module. */
    @Volatile
    var instance: NarrationService? = null
  }
}
