package expo.modules.echowidget

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
) : RemoteViewsService.RemoteViewsFactory {

  private var cards: List<WidgetCard> = emptyList()

  // Modest bitmap size: RemoteViews has a per-widget bitmap memory budget and
  // the ImageView is fitXY, so a small soft mesh upscales fine.
  private val meshW = 380
  private val meshH = 180

  override fun onCreate() {}

  override fun onDataSetChanged() {
    cards = WidgetStore.readCards(context)
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
    rv.setImageViewBitmap(R.id.item_mesh, MeshRenderer.mesh(palette, meshW, meshH))
    rv.setImageViewBitmap(R.id.item_dot, MeshRenderer.dot(palette))
    rv.setTextViewText(R.id.item_sender, card.sender.uppercase())
    rv.setTextViewText(R.id.item_phrase, card.phrase)

    if (card.hasAudio) {
      rv.setViewVisibility(R.id.item_pill, android.view.View.VISIBLE)
      rv.setViewVisibility(R.id.item_wave, android.view.View.VISIBLE)
      rv.setImageViewBitmap(R.id.item_play_icon, MeshRenderer.playIcon(palette, playing))
      rv.setTextViewText(R.id.item_play_label, if (playing) "Playing" else "Listen")
      rv.setImageViewBitmap(R.id.item_wave, MeshRenderer.wave(card.id, playing, palette))
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
  override fun onGetViewFactory(intent: Intent): RemoteViewsFactory =
    EchoWidgetFactory(applicationContext)
}
