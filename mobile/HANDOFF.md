# Mobile app handoff — pick up from here

State as of 2026-06-10. Backend is **feature-complete and tested**; the Expo app is **fully written and type-checks clean**, but has **never been built or run** — that's the next step.

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

1. **Build the Android app** (never done yet — expect issues here):
   ```bash
   cd mobile
   npx expo prebuild --platform android   # generates android/ from app.config.ts
   cd android && ./gradlew assembleDebug  # or: npx expo run:android with device/emulator
   ```
   Machine has: Node 22, JDK 17, Android SDK at `%LOCALAPPDATA%\Android\Sdk` (platforms 31/33/34), **no AVDs, no device attached** — create an AVD or plug in a phone (`adb devices`).
   APK lands at `mobile/android/app/build/outputs/apk/debug/app-debug.apk`.

2. **End-to-end test on device/emulator:**
   - Backend up: `uvicorn app.main:app` + MongoDB + (for real Gmail pushes) ngrok.
   - Emulator reaches host via `http://10.0.2.2:8000` (the app default). Real phone needs the ngrok HTTPS URL typed into the sign-in screen.
   - NOTE: `android.usesCleartextTraffic` may be needed for plain-http 10.0.2.2 — if sign-in fetch fails on emulator with cleartext error, add `"android": { "usesCleartextTraffic": true }` via `expo-build-properties` plugin or use the ngrok https URL even on emulator.
   - Sign in → browser → Google → should bounce back into the app with token. Feed should show cards; play button streams WAV.
   - Add the widget from the launcher's widget picker ("EmailPartner") → shows latest card art + glass panel → tap → app opens and narrates.

3. **Known risks / things not yet verified:**
   - `expo-audio` API names (`createAudioPlayer`, `setAudioModeAsync`, `playbackStatusUpdate`, `status.didJustFinish`) — verify against SDK 56 docs (https://docs.expo.dev/versions/v56.0.0/sdk/audio/) if playback misbehaves; tsc passed so shapes exist.
   - Widget headless fetch: SecureStore + fetch inside `widgetTaskHandler` should work (runs in app process) but is unverified.
   - `ImageWidget` with network image needs INTERNET perm (Expo adds it by default).
   - Gmail OAuth refresh tokens expire after 7 days while the Google OAuth consent screen is in Testing mode — re-sign-in, or publish the app in Google Cloud console.
   - The user's existing Gmail account row had a dead refresh token (invalid_grant in renewal loop) — re-sign-in fixes; optional hardening: mark account on invalid_grant instead of hourly retry-spam (discussed, not built).

4. **Nice-to-haves discussed, not started:** README section for `mobile/`, GCS blob storage, SSE instead of polling (web), narration playback directly from widget without opening the app (needs foreground service).

## Conventions
- Granular conventional commits (`feat(mobile): …`), NO Co-Authored-By trailer.
- Backend tests must stay green: `python -m pytest tests`.
- Don't commit `mobile/android/` — it's generated by prebuild.
