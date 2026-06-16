package expo.modules.echowidget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.widget.RemoteViews

/**
 * Native StackView widget: a swipeable deck of the latest cards. Data comes
 * from WidgetStore (the RN app writes it via EchoWidgetModule); play/stop fires
 * a PendingIntent straight into NarrationService (no JS, instant). The icon
 * flips optimistically on tap, same lesson as the old RN widget.
 */
class EchoWidgetProvider : AppWidgetProvider() {

  override fun onUpdate(context: Context, mgr: AppWidgetManager, ids: IntArray) {
    for (id in ids) {
      val rv = RemoteViews(context.packageName, R.layout.echo_widget)

      val adapter = Intent(context, EchoWidgetService::class.java).apply {
        putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, id)
        // unique data so each widget instance binds its own factory
        data = Uri.parse(toUri(Intent.URI_INTENT_SCHEME))
      }
      rv.setRemoteAdapter(R.id.echo_stack, adapter)
      rv.setEmptyView(R.id.echo_stack, R.id.echo_empty)

      val template = Intent(context, EchoWidgetProvider::class.java).apply {
        action = ACTION_ITEM_CLICK
      }
      rv.setPendingIntentTemplate(
        R.id.echo_stack,
        PendingIntent.getBroadcast(
          context, 0, template,
          PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
        ),
      )

      mgr.updateAppWidget(id, rv)
    }
    mgr.notifyAppWidgetViewDataChanged(ids, R.id.echo_stack)
  }

  override fun onReceive(context: Context, intent: Intent) {
    super.onReceive(context, intent)
    if (intent.action != ACTION_ITEM_CLICK) return

    val id = intent.getStringExtra(EXTRA_ID) ?: return
    when (intent.getStringExtra(EXTRA_KIND)) {
      KIND_PLAY -> togglePlay(context, intent, id)
      KIND_OPEN -> openInApp(context, id)
    }
  }

  private fun togglePlay(context: Context, intent: Intent, id: String) {
    val isPlaying = WidgetStore.readPlayingId(context) == id
    val service = Intent().apply {
      component = ComponentName(context.packageName, NARRATION_SERVICE)
      action = if (isPlaying) NARRATION_STOP else NARRATION_PLAY
      putExtra("id", id)
      putExtra("url", intent.getStringExtra(EXTRA_URL))
      putExtra("title", intent.getStringExtra(EXTRA_TITLE))
      putExtra("artist", intent.getStringExtra(EXTRA_ARTIST))
    }
    try {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        context.startForegroundService(service)
      } else {
        context.startService(service)
      }
    } catch (_: Exception) {
      return
    }
    // optimistic flip; NarrationService also persists the real state + refreshes
    WidgetStore.writePlayingId(context, if (isPlaying) null else id)
    refresh(context)
  }

  private fun openInApp(context: Context, id: String) {
    val view = Intent(Intent.ACTION_VIEW, Uri.parse("emailpartner://read/$id")).apply {
      setPackage(context.packageName)
      addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    try {
      context.startActivity(view)
    } catch (_: Exception) {
    }
  }

  private fun refresh(context: Context) {
    val mgr = AppWidgetManager.getInstance(context)
    val ids = mgr.getAppWidgetIds(ComponentName(context, EchoWidgetProvider::class.java))
    if (ids.isNotEmpty()) mgr.notifyAppWidgetViewDataChanged(ids, R.id.echo_stack)
  }

  companion object {
    const val ACTION_ITEM_CLICK = "expo.modules.echowidget.ITEM_CLICK"
    const val EXTRA_KIND = "kind"
    const val EXTRA_ID = "id"
    const val EXTRA_URL = "url"
    const val EXTRA_TITLE = "title"
    const val EXTRA_ARTIST = "artist"
    const val KIND_PLAY = "play"
    const val KIND_OPEN = "open"

    // NarrationService lives in the sibling module; reference by name to stay
    // compile-decoupled (its action/extra contract is stable).
    private const val NARRATION_SERVICE = "expo.modules.narration.NarrationService"
    private const val NARRATION_PLAY = "expo.modules.narration.PLAY"
    private const val NARRATION_STOP = "expo.modules.narration.STOP"
  }
}
