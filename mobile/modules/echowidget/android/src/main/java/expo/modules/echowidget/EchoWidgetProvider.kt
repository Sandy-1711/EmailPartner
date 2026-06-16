package expo.modules.echowidget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.RemoteViews

/**
 * Native StackView widget: a swipeable deck of the latest cards. Data comes from
 * WidgetStore (the RN app writes it via EchoWidgetModule). Item taps go through
 * EchoWidgetActivity (a widget tap can only start the foreground NarrationService
 * from an activity context — a broadcast FGS start is denied on Android 12+).
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

      val template = Intent(context, EchoWidgetActivity::class.java)
      rv.setPendingIntentTemplate(
        R.id.echo_stack,
        PendingIntent.getActivity(
          context, 0, template,
          PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
        ),
      )

      mgr.updateAppWidget(id, rv)
    }
    mgr.notifyAppWidgetViewDataChanged(ids, R.id.echo_stack)
  }

  companion object {
    const val EXTRA_KIND = "kind"
    const val EXTRA_ID = "id"
    const val EXTRA_URL = "url"
    const val EXTRA_TITLE = "title"
    const val EXTRA_ARTIST = "artist"
    const val KIND_PLAY = "play"
    const val KIND_OPEN = "open"
  }
}
