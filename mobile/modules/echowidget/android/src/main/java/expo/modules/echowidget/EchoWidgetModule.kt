package expo.modules.echowidget

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * JS bridge for the native StackView widget. The RN app calls setCards() with a
 * JSON array of cards whenever it fetches; we persist it and nudge the widget to
 * rebuild its deck. No rendering happens in JS — the widget is fully native.
 */
class EchoWidgetModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("EchoWidget")

    Function("setCards") { json: String ->
      val context = appContext.reactContext ?: return@Function
      WidgetStore.writeCardsJson(context, json)
      notifyWidget(context)
    }

    Function("refresh") {
      val context = appContext.reactContext ?: return@Function
      notifyWidget(context)
    }
  }

  private fun notifyWidget(context: Context) {
    val mgr = AppWidgetManager.getInstance(context)
    val ids = mgr.getAppWidgetIds(ComponentName(context, EchoWidgetProvider::class.java))
    if (ids.isNotEmpty()) mgr.notifyAppWidgetViewDataChanged(ids, R.id.echo_stack)
  }
}
