# Mobile app handoff — pick up from here

State as of 2026-06-10 (evening). Backend is **feature-complete and tested**; the Expo app is **written, type-checks clean, and the debug APK builds successfully** — what's left is running it on an emulator/device.

## What exists and works (all committed on `master`)

### Backend (FastAPI, runs fine)
- Full pipeline: Gmail watch → Pub/Sub webhook → durable Mongo-backed queue (`app/services/queue/worker.py`) → Gemini summary + illustration + **TTS narration** (WAV at `card_audio_url`).
- Web frontend at `/` (`app/static/index.html`): live polling feed, works in browser.
- **Mobile support, already done:**
  - `Authorization: Bearer <session-token>` accepted everywhere via `get_session_user_id` in `app/dependencies.py`.
  - `GET /v1/auth/google/start?client=mobile` → OAuth state carries the flag → callback 303-redirects to `emailpartner://auth?token=<session-token>` instead of setting a cookie (`app/routers/v1/auth/controller.py`).
- Tests: `python -m pytest tests` (21 passing, in-memory DB fake, no Mongo needed).

### Expo app in `mobile/` (written, type-checked, NOT yet built/run)
- Expo SDK 56, RN 0.85, TypeScript. Deps installed: `react-native-android-widget@0.20.3`, `expo-audio`, `expo-web-browser`, `expo-linking`, `expo-secure-store`.
- `app.config.ts` (app.json was deleted): name EmailPartner, `scheme: 'emailpartner'`, `android.package: 'com.emailpartner.app'`, widget plugin config (widget `name: 'EmailCard'`, 4x2 cells, resizable, 30-min `updatePeriodMillis`).
- `src/lib/config.ts` — SecureStore: server URL (default `http://10.0.2.2:8000` for emulator) + session token.
- `src/lib/api.ts` — fetch wrapper adding Bearer header; `getMe/getCards/retryCard/getSignInUrl`; card text helpers (`headlineOf/summaryOf/senderOf` — `text` is `"headline\n\nsummary"`).
- `App.tsx` — auth state machine; deep links: `emailpartner://auth?token=…` (sign-in) and `emailpartner://play/<cardId>` (widget tap → auto-play narration in feed).
- `src/screens/SignInScreen.tsx` — server URL input + `WebBrowser.openAuthSessionAsync(authUrl, 'emailpartner://auth')`, token parsed with `Linking.parse` (NOT `new URL` — Hermes).
- `src/screens/FeedScreen.tsx` — 4s polling feed of `GlassCard`s; audio via `expo-audio` `createAudioPlayer({uri})` (one player at a time, `didJustFinish` clears state); calls `refreshWidget(cards)` after every fetch.
- `src/widget/CardWidget.tsx` — RemoteViews widget: latest ready card's art (`ImageWidget`, network URL cast to `` `https:${string}` ``) under a frosted glass `FlexWidget` panel (headline, sender, "▶ listen"); whole thing `OPEN_URI` → `emailpartner://play/<id>`; empty/signed-out fallback panel with `OPEN_APP`.
- `src/widget/widget-task-handler.tsx` — handles WIDGET_ADDED/UPDATE/RESIZED by fetching cards (Bearer token from SecureStore) and rendering.
- `index.ts` — `registerRootComponent(App)` + `registerWidgetTaskHandler(widgetTaskHandler)`.
- `mobile/.gitignore` ignores `/android` and `/ios` (CNG — native dirs are generated).

## What remains (in order)

1. **Build the Android app — ✅ DONE 2026-06-10.** `expo prebuild` + `gradlew assembleDebug` both succeeded; APK at `mobile/android/app/build/outputs/apk/debug/app-debug.apk` (137 MB, debug).
   Environment fixes that made it work (already applied to this machine):
   - System `JAVA_HOME` points at a nonexistent `C:\Program Files\Java\jdk-19` — **always build with** `JAVA_HOME="C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot" ./gradlew assembleDebug`.
   - SDK's `ndk/27.1.12297006` was a corrupt 1 KB husk → deleted; AGP auto-reinstalled it properly during the build.
   - AVD **`ep_test`** (android-31 google_apis x86_64) was created manually (legacy avdmanager breaks on JDK 17; its two INI files were written by hand in `~/.android/avd/`). Boot with:
     `%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe -avd ep_test -no-snapshot -gpu swiftshader_indirect`
   - Debug manifest already has `usesCleartextTraffic=true`, so plain `http://10.0.2.2:8000` works on the emulator in debug builds.

2. **NEXT STEP — smoke test on emulator/device (nothing run yet):**
   - Boot `ep_test` (command above), wait for `adb shell getprop sys.boot_completed` = 1, then `adb install mobile/android/app/build/outputs/apk/debug/app-debug.apk` and launch `com.emailpartner.app`.
   - Verify: sign-in screen renders → deep link `adb shell am start -a android.intent.action.VIEW -d "emailpartner://auth?token=test"` flips to feed → widget appears in launcher picker.

3. **End-to-end test (needs backend):**
   - Backend up: `uvicorn app.main:app` + MongoDB (not installed on this machine — Docker Desktop exists but wasn't running) + ngrok for real Gmail pushes.
   - Emulator reaches host via `http://10.0.2.2:8000` (the app default). Real phone needs the ngrok HTTPS URL typed into the sign-in screen.
   - Sign in → browser → Google → should bounce back into the app with token. Feed should show cards; play button streams WAV.
   - Add the widget from the launcher's widget picker ("EmailPartner") → shows latest card art + glass panel → tap → app opens and narrates.

4. **Known risks / things not yet verified:**
   - `expo-audio` API names (`createAudioPlayer`, `setAudioModeAsync`, `playbackStatusUpdate`, `status.didJustFinish`) — verify against SDK 56 docs (https://docs.expo.dev/versions/v56.0.0/sdk/audio/) if playback misbehaves; tsc passed so shapes exist.
   - Widget headless fetch: SecureStore + fetch inside `widgetTaskHandler` should work (runs in app process) but is unverified.
   - `ImageWidget` with network image needs INTERNET perm (Expo adds it by default).
   - Gmail OAuth refresh tokens expire after 7 days while the Google OAuth consent screen is in Testing mode — re-sign-in, or publish the app in Google Cloud console.
   - The user's existing Gmail account row had a dead refresh token (invalid_grant in renewal loop) — re-sign-in fixes; optional hardening: mark account on invalid_grant instead of hourly retry-spam (discussed, not built).

5. **Nice-to-haves discussed, not started:** GCS blob storage, SSE instead of polling (web), narration playback directly from widget without opening the app (needs foreground service), invalid_grant hardening in the watch renewal loop. (README mobile section: done.)

## Conventions
- Granular conventional commits (`feat(mobile): …`), NO Co-Authored-By trailer.
- Backend tests must stay green: `python -m pytest tests`.
- Don't commit `mobile/android/` — it's generated by prebuild.
