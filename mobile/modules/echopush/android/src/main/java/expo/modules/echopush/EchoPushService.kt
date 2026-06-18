package expo.modules.echopush

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.json.JSONArray
import org.json.JSONObject

/**
 * Receives FCM and surfaces a freshly-narrated email even when the app is dead.
 *
 * The backend sends DATA-only messages (no `notification` payload) so this
 * handler always runs and builds a rich notification with a Listen action — a
 * `notification` payload would be auto-shown by the system and skip onMessage
 * while backgrounded. On each message we:
 *   1. prepend the card into the widget's store + nudge the widget to re-read,
 *   2. post a per-email notification whose Listen action starts the foreground
 *      NarrationService directly (a notification-action FGS start is an
 *      Android-12+ exemption, so no trampoline activity is needed here).
 */
class EchoPushService : FirebaseMessagingService() {

  override fun onNewToken(token: String) {
    // Cache so JS can read the latest even before its event listener attaches;
    // also emit live if the JS module is alive so it can re-register with the API.
    getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_TOKEN, token).apply()
    EchoPushModule.emitToken(token)
  }

  override fun onMessageReceived(message: RemoteMessage) {
    val d = message.data
    val id = d["id"] ?: return
    val phrase = d["phrase"].orEmpty()
    val sender = d["sender"].orEmpty()
    val tone = d["tone"]
    val audioUrl = d["audio_url"]?.takeIf { it.isNotBlank() }

    upsertWidgetCard(id, phrase, sender, tone, audioUrl)
    refreshWidget()
    postNotification(id, phrase, sender, audioUrl)
  }

  // ---- widget store (decoupled from the echowidget module: literal names,
  // mirrors NarrationService's SharedPreferences contract — keep in sync) ----

  private fun upsertWidgetCard(
    id: String, phrase: String, sender: String, tone: String?, audioUrl: String?,
  ) {
    val prefs = getSharedPreferences(WIDGET_PREFS, MODE_PRIVATE)
    val arr = try {
      JSONArray(prefs.getString(WIDGET_KEY_CARDS, null) ?: "[]")
    } catch (_: Exception) {
      JSONArray()
    }
    val card = JSONObject().apply {
      put("id", id)
      put("phrase", phrase)
      put("sender", sender)
      put("tone", tone ?: JSONObject.NULL)
      put("hasAudio", audioUrl != null)
      put("audioUrl", audioUrl ?: JSONObject.NULL)
    }
    // newest first, drop any existing entry for this id, cap the deck
    val out = JSONArray().put(card)
    for (i in 0 until arr.length()) {
      val o = arr.optJSONObject(i) ?: continue
      if (o.optString("id") == id) continue
      if (out.length() >= MAX_CARDS) break
      out.put(o)
    }
    prefs.edit().putString(WIDGET_KEY_CARDS, out.toString()).apply()
  }

  private fun refreshWidget() {
    try {
      val component = ComponentName(this, ECHO_WIDGET_PROVIDER)
      sendBroadcast(Intent(ECHO_WIDGET_REFRESH).setComponent(component))
    } catch (_: Exception) {
    }
  }

  // ---- notification ----

  private fun postNotification(id: String, phrase: String, sender: String, audioUrl: String?) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
      ContextCompat.checkSelfPermission(this, "android.permission.POST_NOTIFICATIONS") !=
      PackageManager.PERMISSION_GRANTED
    ) {
      return // user hasn't granted notifications; nothing we can do silently
    }

    val manager = getSystemService(NotificationManager::class.java)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
      manager.getNotificationChannel(CHANNEL_ID) == null
    ) {
      manager.createNotificationChannel(
        NotificationChannel(CHANNEL_ID, "New emails", NotificationManager.IMPORTANCE_HIGH)
      )
    }

    val openIntent = PendingIntent.getActivity(
      this, id.hashCode(),
      Intent(Intent.ACTION_VIEW, Uri.parse("emailpartner://read/$id")).setPackage(packageName),
      PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )

    val builder = NotificationCompat.Builder(this, CHANNEL_ID)
      .setSmallIcon(android.R.drawable.ic_dialog_email)
      .setContentTitle(sender.ifBlank { "Echo Mail" })
      .setContentText(phrase)
      .setStyle(NotificationCompat.BigTextStyle().bigText(phrase))
      .setAutoCancel(true)
      .setContentIntent(openIntent)
      .setPriority(NotificationCompat.PRIORITY_HIGH)

    if (audioUrl != null) {
      val play = Intent().apply {
        component = ComponentName(packageName, NARRATION_SERVICE)
        action = NARRATION_PLAY
        putExtra("id", id)
        putExtra("url", audioUrl)
        putExtra("title", phrase)
        putExtra("artist", sender)
      }
      val listen = PendingIntent.getForegroundService(
        this, id.hashCode(), play,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
      )
      builder.addAction(android.R.drawable.ic_media_play, "Listen", listen)
    }

    NotificationManagerCompat.from(this).notify(id.hashCode(), builder.build())
  }

  companion object {
    const val PREFS = "echo_push"
    const val KEY_TOKEN = "token"
    const val CHANNEL_ID = "echo_emails"

    // mirrors WidgetStore (echowidget) — kept decoupled by literal name
    private const val WIDGET_PREFS = "echo_widget"
    private const val WIDGET_KEY_CARDS = "cards"
    private const val MAX_CARDS = 10
    private const val ECHO_WIDGET_PROVIDER = "expo.modules.echowidget.EchoWidgetProvider"
    private const val ECHO_WIDGET_REFRESH = "expo.modules.echowidget.REFRESH"

    // mirrors NarrationService contract
    private const val NARRATION_SERVICE = "expo.modules.narration.NarrationService"
    private const val NARRATION_PLAY = "expo.modules.narration.PLAY"
  }
}
