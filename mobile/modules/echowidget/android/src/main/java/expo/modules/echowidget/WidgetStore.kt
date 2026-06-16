package expo.modules.echowidget

import android.content.Context
import org.json.JSONArray

/** One card as shown in the widget; mirrors src/widget/CardWidget WidgetCard. */
data class WidgetCard(
  val id: String,
  val phrase: String,
  val sender: String,
  val tone: String?,
  val hasAudio: Boolean,
  val audioUrl: String?,
)

/**
 * The widget's data source. The RN app owns the truth and writes a JSON array
 * here (EchoWidgetModule.setCards) whenever it fetches; the widget's
 * RemoteViewsFactory reads it on the launcher's schedule. Plain SharedPreferences
 * (not expo-secure-store) so the native widget process can read it directly with
 * no network and no JS.
 */
object WidgetStore {
  // Shared with NarrationService (it writes KEY_PLAYING by literal name so the
  // two native modules stay compile-decoupled). Keep this name in sync there.
  const val PREFS = "echo_widget"
  private const val KEY_CARDS = "cards"
  const val KEY_PLAYING = "playing_id"

  private fun prefs(context: Context) =
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

  fun writeCardsJson(context: Context, json: String) {
    prefs(context).edit().putString(KEY_CARDS, json).apply()
  }

  /** Card id the NarrationService is currently playing, or null. */
  fun readPlayingId(context: Context): String? =
    prefs(context).getString(KEY_PLAYING, null)

  /** Optimistic write so the play/stop icon flips instantly on tap. */
  fun writePlayingId(context: Context, id: String?) {
    prefs(context).edit().putString(KEY_PLAYING, id).apply()
  }

  fun readCards(context: Context): List<WidgetCard> {
    val raw = prefs(context).getString(KEY_CARDS, null) ?: return emptyList()
    return try {
      val arr = JSONArray(raw)
      (0 until arr.length()).mapNotNull { i ->
        val o = arr.optJSONObject(i) ?: return@mapNotNull null
        WidgetCard(
          id = o.optString("id"),
          phrase = o.optString("phrase"),
          sender = o.optString("sender"),
          tone = if (o.isNull("tone")) null else o.optString("tone"),
          hasAudio = o.optBoolean("hasAudio"),
          audioUrl = if (o.isNull("audioUrl")) null else o.optString("audioUrl"),
        )
      }
    } catch (_: Exception) {
      emptyList()
    }
  }
}
