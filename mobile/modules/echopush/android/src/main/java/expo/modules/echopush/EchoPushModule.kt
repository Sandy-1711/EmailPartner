package expo.modules.echopush

import com.google.firebase.messaging.FirebaseMessaging
import expo.modules.interfaces.permissions.Permissions
import expo.modules.kotlin.Promise
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

private const val POST_NOTIFICATIONS = "android.permission.POST_NOTIFICATIONS"

/**
 * JS bridge for FCM. The app fetches its device token and registers it with the
 * backend (api.ts) so the worker can push freshly-narrated emails; the actual
 * receive/notify/widget-refresh happens natively in EchoPushService, even when
 * the app is closed. Wrapped on the JS side so it no-ops on older binaries.
 */
class EchoPushModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("EchoPush")

    Events("onTokenRefresh")

    OnCreate { instance = this@EchoPushModule }
    OnDestroy { instance = null }

    AsyncFunction("getToken") { promise: Promise ->
      FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
        if (task.isSuccessful) {
          promise.resolve(task.result)
        } else {
          promise.reject("ERR_FCM_TOKEN", task.exception?.message ?: "token fetch failed", task.exception)
        }
      }
    }

    AsyncFunction("requestPermission") { promise: Promise ->
      Permissions.askForPermissionsWithPermissionsManager(
        appContext.permissions, promise, POST_NOTIFICATIONS,
      )
    }

    AsyncFunction("getPermission") { promise: Promise ->
      Permissions.getPermissionsWithPermissionsManager(
        appContext.permissions, promise, POST_NOTIFICATIONS,
      )
    }
  }

  companion object {
    @Volatile
    private var instance: EchoPushModule? = null

    /** Emit a refreshed token to JS if the module is alive (no-op otherwise). */
    fun emitToken(token: String) {
      instance?.sendEvent("onTokenRefresh", mapOf("token" to token))
    }
  }
}
