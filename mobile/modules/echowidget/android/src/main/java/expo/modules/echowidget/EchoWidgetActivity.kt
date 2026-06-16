package expo.modules.echowidget

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle

/**
 * Invisible trampoline for widget item taps. A StackView collection only allows
 * ONE pendingIntentTemplate, and — critically — a widget tap can only start a
 * foreground service from an ACTIVITY context (the tap briefly makes the app
 * foreground). Starting NarrationService from the provider's BroadcastReceiver
 * is denied as a background FGS start. So every item click lands here, and we
 * either toggle playback or open the email, then finish immediately.
 */
class EchoWidgetActivity : Activity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val id = intent.getStringExtra(EchoWidgetProvider.EXTRA_ID)
    if (id != null) {
      when (intent.getStringExtra(EchoWidgetProvider.EXTRA_KIND)) {
        EchoWidgetProvider.KIND_PLAY -> togglePlay(id)
        EchoWidgetProvider.KIND_OPEN -> openEmail(id)
      }
    }
    finish()
  }

  private fun togglePlay(id: String) {
    val isPlaying = WidgetStore.readPlayingId(this) == id
    val service = Intent().apply {
      component = ComponentName(packageName, NARRATION_SERVICE)
      action = if (isPlaying) NARRATION_STOP else NARRATION_PLAY
      putExtra("id", id)
      putExtra("url", intent.getStringExtra(EchoWidgetProvider.EXTRA_URL))
      putExtra("title", intent.getStringExtra(EchoWidgetProvider.EXTRA_TITLE))
      putExtra("artist", intent.getStringExtra(EchoWidgetProvider.EXTRA_ARTIST))
    }
    // Only start the service and finish. Do NOT touch AppWidgetManager here —
    // notifyAppWidgetViewDataChanged binds the collection service to this
    // activity, which then finishes and leaks/tears down the connection,
    // killing the StackView adapter (that was the widget "crash"). The play
    // icon refreshes from NarrationService (a long-lived service context).
    try {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        startForegroundService(service)
      } else {
        startService(service)
      }
    } catch (_: Exception) {
    }
  }

  private fun openEmail(id: String) {
    try {
      startActivity(
        Intent(Intent.ACTION_VIEW, Uri.parse("emailpartner://read/$id")).apply {
          setPackage(packageName)
          addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
      )
    } catch (_: Exception) {
    }
  }

  companion object {
    private const val NARRATION_SERVICE = "expo.modules.narration.NarrationService"
    private const val NARRATION_PLAY = "expo.modules.narration.PLAY"
    private const val NARRATION_STOP = "expo.modules.narration.STOP"
  }
}
