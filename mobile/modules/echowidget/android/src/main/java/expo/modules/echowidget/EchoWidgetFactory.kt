package expo.modules.echowidget

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import android.widget.RemoteViewsService

/**
 * Builds one RemoteViews per card for the StackView deck. The mesh / dot / play
 * icon / waveform are Kotlin-drawn bitmaps (real blur, glows); sender + phrase
 * are crisp native TextViews. Clicks use fill-in intents merged into the
 * provider's pendingIntentTemplate.
 */
class EchoWidgetFactory(
  private val context: Context,
  private val appWidgetId: Int,
) : RemoteViewsService.RemoteViewsFactory {

  private var cards: List<WidgetCard> = emptyList()

  // Mesh aspect matches the widget (so fitXY doesn't stretch the rounded
  // corners), but kept SMALL on purpose: a RemoteViews item must fit in a
  // ~1MB Binder transaction, and the soft mesh upscales fine. 420x180 ARGB is
  // ~300KB; going large (600x360 ~864KB) overran the transaction and the host
  // dropped the whole widget on the play-tap rebuild.
  private var meshW = 400
  private var meshH = 180

  override fun onCreate() {
    computeMeshSize()
  }

  override fun onDataSetChanged() {
    computeMeshSize()
    cards = WidgetStore.readCards(context)
  }

  private fun computeMeshSize() {
    val opts = AppWidgetManager.getInstance(context).getAppWidgetOptions(appWidgetId)
    val wDp = opts.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_WIDTH, 0)
    val hDp = opts.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 0)
    val aspect = if (wDp > 0 && hDp > 0) wDp.toFloat() / hDp else 2.1f
    meshH = 180
    meshW = (meshH * aspect).toInt().coerceIn(240, 420)
  }

  override fun onDestroy() {
    cards = emptyList()
  }

  override fun getCount(): Int = cards.size

  override fun getViewAt(position: Int): RemoteViews {
    val card = cards[position]
    val palette = Palettes.forTone(card.tone)
    val playing = card.hasAudio && card.id == WidgetStore.readPlayingId(context)

    val rv = RemoteViews(context.packageName, R.layout.echo_widget_item)
    // Never let a rendering hiccup break the whole widget — fall back to a
    // solid tone background if a bitmap can't be drawn/sent.
    try {
      rv.setImageViewBitmap(R.id.item_mesh, MeshRenderer.mesh(palette, meshW, meshH))
      rv.setImageViewBitmap(R.id.item_dot, MeshRenderer.dot(palette))
    } catch (_: Throwable) {
      rv.setInt(R.id.item_mesh, "setBackgroundColor", palette.base)
    }
    rv.setTextViewText(R.id.item_sender, card.sender.uppercase())
    rv.setTextViewText(R.id.item_phrase, card.phrase)

    if (card.hasAudio) {
      rv.setViewVisibility(R.id.item_pill, android.view.View.VISIBLE)
      rv.setViewVisibility(R.id.item_wave, android.view.View.VISIBLE)
      try {
        rv.setImageViewBitmap(R.id.item_play_icon, MeshRenderer.playIcon(palette, playing))
        rv.setImageViewBitmap(R.id.item_wave, MeshRenderer.wave(card.id, playing, palette))
      } catch (_: Throwable) {
      }
      rv.setTextViewText(R.id.item_play_label, if (playing) "Playing" else "Listen")
      rv.setOnClickFillInIntent(R.id.item_pill, playFillIn(card))
    } else {
      rv.setViewVisibility(R.id.item_pill, android.view.View.GONE)
      rv.setViewVisibility(R.id.item_wave, android.view.View.GONE)
    }

    // tapping the card body opens the email in the app
    rv.setOnClickFillInIntent(R.id.item_root, openFillIn(card))
    return rv
  }

  private fun playFillIn(card: WidgetCard): Intent = Intent().apply {
    putExtra(EchoWidgetProvider.EXTRA_KIND, EchoWidgetProvider.KIND_PLAY)
    putExtra(EchoWidgetProvider.EXTRA_ID, card.id)
    putExtra(EchoWidgetProvider.EXTRA_URL, card.audioUrl)
    putExtra(EchoWidgetProvider.EXTRA_TITLE, card.phrase)
    putExtra(EchoWidgetProvider.EXTRA_ARTIST, card.sender)
  }

  private fun openFillIn(card: WidgetCard): Intent = Intent().apply {
    putExtra(EchoWidgetProvider.EXTRA_KIND, EchoWidgetProvider.KIND_OPEN)
    putExtra(EchoWidgetProvider.EXTRA_ID, card.id)
  }

  override fun getLoadingView(): RemoteViews? = null
  override fun getViewTypeCount(): Int = 1
  override fun getItemId(position: Int): Long = cards.getOrNull(position)?.id?.hashCode()?.toLong() ?: position.toLong()
  override fun hasStableIds(): Boolean = true
}

class EchoWidgetService : RemoteViewsService() {
  override fun onGetViewFactory(intent: Intent): RemoteViewsFactory {
    val appWidgetId = intent.getIntExtra(
      AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID
    )
    return EchoWidgetFactory(applicationContext, appWidgetId)
  }
}
