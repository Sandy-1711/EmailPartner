# Echo Mail (EmailPartner mobile) — handoff

State as of 2026-06-16 (late). Backend feature-complete + tested. App implements the Echo Mail design; audio works app + widget via the native NarrationService. The user is frustrated with iteration count — fix precisely, verify before claiming done, no scattershot changes. Granular commits during work, no Co-Authored-By. **Never `gpgconf --kill gpg-agent` (it forces a password prompt that times out) — just retry `git commit`.**

**OPEN ISSUE → the native StackView widget (work-plan #4). The latest build is installed on the phone (HEAD 71860c5).** This session's wins (flood guard, Skia mesh, UI-thread scrub, seek-on-non-playing, the native widget plumbing + crash/vanish/size fixes) are all committed. The widget FUNCTIONS now (full-size card, play doesn't crash, cards don't vanish) but the user still dislikes the StackView aesthetic — see #4 for the recommended redesign (full-bleed card + ‹/› arrows). The user called a hard stop here; pick up at #4 or #5 next session.

## DONE 2026-06-16 (verified working on the emulator `ep_test`)

- **Both prior widget bugs are FIXED + user-verified** (no longer open): widget mesh renders via inline `SvgWidget` string (`src/widget/meshSvg.ts`, commit d155b3c) and the play/stop icon flips instantly from a SecureStore snapshot (`src/widget/cache.ts`, commit d82c1d0).
- **Skia + Reanimated + Gesture Handler + Worklets added** (commit b554dfc): babel uses `react-native-worklets/plugin`; `index.ts` imports `react-native-gesture-handler` first; App root wrapped in `GestureHandlerRootView`.
- **In-app MeshGradient → real Skia gaussian blur** (commit ab02dea): blobs are radial-gradient Circles under a Skia `Blur` image filter; drift + accelerometer tilt run as reanimated worklets on the UI thread. `useTilt` now returns SharedValues (was Animated.Value).
- **Hero waveform scrub → UI thread** (gesture-handler Pan + reanimated, commits ecc45c5 / 07c8077 / 44d1350). Key fixes that made it actually work:
  - The hero player is inside an RN `<Modal>`, a SEPARATE native window outside the app-root `GestureHandlerRootView` — gestures got NO touches until a nested `GestureHandlerRootView` was added inside the Modal (EmailModal). **Any gesture inside an RN Modal needs its own root.**
  - Pan gated to horizontal (`activeOffsetX`/`failOffsetY`) + a raced `Tap`, so it coexists with the Detail ScrollView and keeps tap-to-seek.
  - **Seek works on non-playing cards now** (user request): `usePlayback.seek(card, f)` seeks the loaded track, or starts a stopped card and applies the scrub once duration loads (`pendingSeekRef`, resolved in the status poll).
  - Reanimated strict-mode "writing to value during render" fixed by moving the progress mirror into an effect.

## NEXT — agreed work plan 2026-06-16 (in priority order)

User chose these; explicitly NOT doing real-backend-run, web frontend, or local-LLM this round.
1. ✅ **Gmail backfill flood guard (backend).** DONE (commit 86279cb): `_process_history` checks each message's Date via a cheap metadata fetch and skips anything older than `GMAIL_MAX_EMAIL_AGE_SECONDS` (default 1h; 0 disables) before downloading the body or enqueuing. No webhook test harness existed, so no unit test added (logic is a date compare).
2. ✅ **Widget UI polish (RN, fallback).** DONE (commit 163db72) on the old RN widget — superseded by #4 below. Verify-on-phone never happened before the native pivot.
3. ⏳ **Per-email notifications** with a Listen action (the real "always awake" channel — Android has no lock-screen widgets). Plan: post natively (NotificationCompat) with a Listen action `PendingIntent` straight to `NarrationService` (same contract the widget uses: ACTION_PLAY + EXTRA_ID/URL/TITLE/ARTIST), tap → `emailpartner://read/<id>`. App posts when a newly-ready card appears (background delivery waits on #5/FCM). Build it as another local module (mirror modules/echowidget) or fold into echowidget.
4. ⚠️ **NATIVE swipeable StackView widget — BUILT but the user is UNHAPPY with the look; likely needs a redesign.** Local module `modules/echowidget` (commit 49f22ee), then a chain of on-device fixes (latest HEAD 71860c5). Architecture (keep this — it's sound):
   - `MeshRenderer` (Kotlin Canvas + `BlurMaskFilter`) draws a real-blur mesh + glowing dot / play-icon / waveform bitmaps. Crisp native `TextView` for sender/phrase.
   - Data: RN app pushes cards `src/lib/echowidget` → `EchoWidgetModule.setCards` → SharedPreferences `echo_widget`/`cards`; `EchoWidgetFactory` reads it (no JS, no network).
   - Taps go through an INVISIBLE trampoline `EchoWidgetActivity` (template = `getActivity`). REASON: a widget tap can only start the FG `NarrationService` from an activity context — a broadcast-context FGS start is DENIED on Android 12+ (`Background started FGS: Disallowed, uidState RCVR`). The trampoline ONLY starts/stops the service then `finish()`es — it must NOT call `AppWidgetManager` (doing so leaked a ServiceConnection that tore down the StackView adapter → "crash").
   - Play-state refresh: `NarrationService.notifyWidget()` sends a CUSTOM `expo.modules.echowidget.REFRESH` broadcast → provider does `notifyAppWidgetViewDataChanged` ONLY (data refresh). Do NOT send `APPWIDGET_UPDATE` for this — it re-runs `onUpdate`+`setRemoteAdapter` and RESETS the deck (cards vanish until scroll).
   - Bitmaps MUST stay small (≤ ~420×180, <1MB) or the RemoteViews Binder transaction overflows and the host drops the widget.
   - StackView item layout MUST NOT use `layout_weight` — StackView measures items in a way that collapses weighted children to zero, shrinking the card. Use the FrameLayout + `layout_gravity` layout (restored from 49f22ee).
   - **STILL UNSATISFACTORY (user: "broke it", "looks shit", "half the page", "cards different sizes"):** StackView inherently offsets+shrinks the peeking card and reserves margins for the 3D stack — not configurable. After all fixes the front card is full-size again, play no longer crashes, cards no longer vanish — but the overall STACK aesthetic still reads as janky to the user. **RECOMMENDED NEXT: drop StackView for a cleaner look** — a single full-bleed card filling the whole widget + small ‹/› buttons (or an `AdapterViewFlipper`) to move between emails. Loses the swipe gesture but looks polished and predictable. Confirm with the user before rebuilding. (~20 min full build after `prebuild --clean`; incremental module rebuilds are ~50s via `./gradlew :app:installDebug`.)
5. ⏳ **FCM push-fresh widget + notifications (#3 + #5) — NOW UNBLOCKED.** User added `google-services.json` at the REPO ROOT (`d:/EmailPartner/google-services.json`) — move/copy it into `mobile/` and set `android.googleServicesFile: "./google-services.json"` in app.config.ts, add the Firebase config plugin / FCM dep. Then a native `FirebaseMessagingService` posts the per-email notification (Listen action → `NarrationService` ACTION_PLAY with EXTRA_ID/URL/TITLE/ARTIST) + calls the widget REFRESH, even when the app is closed. #3 notifications and #5 FCM are the same workstream now.
6. ⏳ **Dead code cleanup:** DONE — deleted old RN widget (task handler, CardWidget, cache, meshSvg) + `assets/mesh/widget-*.png` + `icon-*.png`. STILL TODO: remove the `react-native-android-widget` npm dep (now unused), and remove `expo-audio` (NarrationService owns all playback) + its config plugin.

## What is VERIFIED WORKING on the user's phone (don't break it)
- Audio from app AND widget via native NarrationService (single ExoPlayer, foreground MediaSessionService, media3 1.9). Play, stop, no app-kill (startForeground called synchronously in onStartCommand — keep this).
- Widget tap-to-toggle with instant icon flip (renders from click payload, no fetch).
- Seek/scrub on the hero waveform: UI-thread gesture-handler Pan + reanimated, commit-on-release, works on playing AND non-playing cards. Waveform pulse animation REMOVED at user request — do not re-add.
- Stereo "speaker+earpiece" output is the phone's stereo pair (Motorola) — normal, not a bug.
- Crash classes fixed: never swap/remove a native-driven Animated transform (Fabric 'forEach of null'); never let startForegroundService run without an immediate startForeground.

## Feedback round 5 (committed)
- **App-kill fixed**: NarrationService now calls startForeground synchronously in onStartCommand (minimal notification, media3 replaces it). Root cause: fast play->stop toggles beat media3's foreground promotion → ForegroundServiceDidNotStartInTimeException killed the process.
- **Widget icon lag fixed**: WIDGET_CLICK re-renders instantly from the click payload (the old path awaited an HTTP fetch first). Toggle logic was verified correct via logs (currentId alternates per tap).
- **Blank widget explained**: ImageWidget assets load via Metro in debug; Metro down → whole bitmap renders empty while clicks still work. Widget is now image-free (gradient + text). Mesh bitmaps can return in release builds (assets bundled) — assets still in `assets/mesh/`.
- Waveform: six staggered per-bar pulses (permanently-attached Animated nodes — NEVER swap/remove a native-driven transform, Fabric crashes).
- "Speaker + earpiece" on the user's Motorola = stereo speaker pair (earpiece is the top channel for media) — normal behavior, explained, not a bug.

## Feedback round 4b (committed; needs on-device verification)
- **ALL playback now runs in the native NarrationService** — the app's `usePlayback` sends play/pausePlay/seekToMs commands and mirrors `getStatus()` at 4Hz. Why: dual speaker+earpiece output came from two audio stacks (expo-audio in-app + ExoPlayer widget service). expo-audio is no longer used for playback (still installed; could be removed later along with its config).
- Crash on stop fixed (Animated transform must never swap to undefined — RN throws 'forEach of null').
- Seek offset fixed (Android locationX is child-relative; use pageX minus measured container origin).
- Verified by user on device: widget plays headlessly via the service (no FGS error). Still to verify after this rebuild: widget tap-to-stop, widget icon flip (temporary console.log markers '[widget]' are in the task handler — REMOVE once diagnosed), lock-screen card, single-output audio, in-app pause/resume/seek through the service.

## Feedback round 4 (committed; needs on-device verification)
- **Native NarrationService** (`mobile/modules/narration/` — local Expo module, Kotlin, media3 1.9): singleton foreground MediaSessionService + ExoPlayer for widget playback. Fixes, by design: widget stop (service intent, no JS handle), the "failed to start expo-audio foreground service" error (we start ours synchronously inside the widget tap's background-FGS allowance), dual speaker+earpiece audio (orphan players gone — single player), lock-screen controls from the widget. App playback calls `Narration.stop()` before starting. NOTE: requires the rebuilt APK; JS wrapper no-ops on older binaries.
- Seek rework: drag scrubs locally at 60fps with a visible scrub line, native seek commits on release; filled waveform bars pulse while playing (4 staggered native-driver loops).
- If widget verification fails next: check `adb logcat | grep -i narration` for service start denials; fallback is making the service `START_STICKY` or routing the widget tap via PendingIntent.getForegroundService from the native side.

## Feedback round 2+3 (all committed)
- Play/pause icon instant (ticker no longer overrides intent while buffering); press-in **preload** so audio starts faster; **waveform scrubbing** (tap/drag the hero waveform to seek).
- Widget stop made reliable: playing-id persisted in SecureStore + `setIsAudioActiveAsync(false)` as a native pause-all kill switch (the headless JS context dies between taps, handles can't be trusted). Bitmap play/stop icons (`assets/mesh/icon-*.png`) replace text glyphs; play pill has its own small ripple.
- Widget background = pre-rendered mesh bitmaps per tone (`assets/mesh/widget-*.png`, PIL-generated — regenerate via script in git history if palettes change).
- Cards: circular corner blobs + film grain; screens: the ORIGINAL full-bleed ambient layout (user preferred it; `BLOBS_AMBIENT` vs `BLOBS_CARD` in MeshGradient).
- Tweaks now six: motion, hue, font, density, blobs(2-4), grain.
- Still open from user feedback: per-email lock-screen notifications with Listen action, swipeable stack in the widget (ListWidget), FCM-fresh widget, font-family tweak, release build, real backend run.

## Latest session (feedback round 1 — all committed)
- Speaker routing fixed (`shouldRouteThroughEarpiece: false`).
- **Widget plays narration headlessly** — play button fires custom `WIDGET_CLICK` handled in the JS task handler, which creates the player + MediaSession there; the app never opens. UNVERIFIED on a real device — emulator can't place widgets via adb. If playback dies when the headless context ends, the fallback is a tiny native foreground service.
- Mesh blobs: gaussian falloff (they read as glow now, were visible circles).
- **Tweaks panel** (sliders icon in header): hue rotate (Indigo/Magenta/Ocean/Forest, HSL math in `src/tweaks.tsx`), motion off/calm/normal/lively, font S/M/L, density — persisted in SecureStore, applied app-wide via TweaksProvider.
- Lucide icons everywhere; **strictly no emojis** (user rule). Widget keeps geometric text chars (RemoteViews limitation).

## User's remaining wishlist (= roadmap, in their priority language)
1. **"Always awake" lock-screen + widget with swipeable email stack.** Reality: Android has no lock-screen widgets (removed in 5.0). The channel is **notifications**: post a rich notification per new email (phrase + Listen action that triggers headless playback — same mechanism as the widget play). Swipeable stack IN the widget is possible via the library's collection/ListWidget support (`RNWidgetCollectionService` exists) — render each email as a list row. Both are designed, not built.
2. **Audio lag on tap** — mostly debug-build JS + WAV buffering. Fixes: release build, and preloading the player for the newest card.
3. **Push-fresh widget** — currently app-poll + 30-min cycle; the real answer is FCM push from the backend worker when a card turns ready.
4. **Agentic + memory features** (future) — keep the app architecture clean for it: api.ts is the only network seam, playback is one hook, tones/tweaks are contexts.

## What's DONE

### Backend (FastAPI + Mongo, 21 tests green: `python -m pytest tests`)
- Gmail watch → Pub/Sub webhook → durable Mongo-claim queue (`app/services/queue/worker.py`, survives restarts via lease sweep) → Gemini summary + illustration + TTS narration (WAV).
- Cards API: phrase + tone persisted (`card_phrase`/`card_tone`), `GET /v1/cards/{id}` returns the full body, session cookie **or** `Authorization: Bearer` auth.
- Mobile OAuth: `GET /v1/auth/google/start?client=mobile` → callback 303s to `emailpartner://auth?token=…`.
- Web frontend at `/` (older glassmorphism design — NOT yet updated to Echo Mail).

### Mobile app (`mobile/`, Expo SDK 56, TypeScript, tsc-clean)
**Design = "Echo Mail"** from the Claude Design bundle (tokens in the repo now; original bundle: claude.ai/design "Email Widget Dashboard" project):
- `src/tones.ts` — indigo/violet/blue tone palettes (urgent→magenta, social→teal, informative/transactional→indigo, promotional→violet). Never orange, no glassmorphism.
- `src/components/MeshGradient.tsx` — the moving 4-blob mesh: SVG radial gradients + the design's meshA–D drift keyframes + accelerometer tilt parallax (`useTilt`, gravity-based — DeviceMotion.rotation is null on many phones).
- `src/components/WavePlayer.tsx` — deterministic 44-bar waveform per email id, accent play circle, fills with real playback progress.
- Screens: Inbox (ambient mesh, tone cards with phrase hero + play-pill), Detail (full-screen mesh, hero player, "The gist", expandable full email), Sign-in. Space Grotesk throughout (`@expo-google-fonts/space-grotesk`).
- `src/hooks/usePlayback.ts` — single app-wide player; **lock-screen media controls** via expo-audio's MediaSession (`setActiveForLockScreen`: phrase=title, sender=artist; audio mode `doNotMix` + `shouldPlayInBackground` — both required). Active card toggles pause/resume; UI syncs when paused from the notification.
- Widget (`src/widget/CardWidget.tsx`): Echo Mail style — tone gradient, glowing dot + label, phrase, static mini waveform; Listen deep-links `emailpartner://play/<id>`, card body `emailpartner://read/<id>` (opens Detail).

### Widget dependency verdict (`react-native-android-widget@0.20.3`)
The library renders the widget tree to a **bitmap** shown in an ImageView with `scaleType="matrix"` (no scaling, top-left anchored; see `RNWidget.java` / `rn_widget.xml`). Bitmap size comes from the launcher's `getAppWidgetOptions` *estimate* — when launchers over-report (common on OEM launchers), the bitmap clips at the **bottom/right**. That was the user's cutoff. Mitigation shipped: a transparent 6dp safety inset around the card absorbs clipping. The lib is otherwise sound; if cutoff persists, increase the inset or re-render on `WIDGET_RESIZED` (already handled).

## Build / test env (already solved — don't rediscover)
- `JAVA_HOME="C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot"` (system JAVA_HOME is broken). Build+install debug: `cd mobile/android && ./gradlew :app:installDebug` (autolinks new native modules without a prebuild; first Skia build ~20 min).
- AVD `ep_test` exists (hand-written INI; avdmanager breaks on JDK 17): `emulator -avd ep_test`. Physical phone `ZA222LJR2B` also used.
- No real backend needed: `C:\Users\sandy\AppData\Local\Temp\mock_ep.py` (mock API on :8000, fake instant sign-in, fake cards). `adb reverse tcp:8081 tcp:8081` + `tcp:8000 tcp:8000`, server URL `http://localhost:8000`. Debug APK needs Metro (`npx expo start`).
- Skia logs `RNSkia: updateAndRelease() failed ... can safely be ignored` every frame on the emulator's software GPU — benign, not an error.

## DEFERRED (not this round, per user 2026-06-16)
- **Run against the real backend** — Mongo + `uvicorn app.main:app` + ngrok + real Google sign-in; real TTS replaces fake.wav. (Do the backfill flood guard FIRST — see work plan #1 — or it burns credits.)
- **Release APK** (standalone): `cd mobile/android && gradlew assembleRelease`. Will also surface the real "audio lag on tap" (debug JS is slow).
- **Local LLM** (OpenAI-compatible `LLMProvider` Ollama/LM Studio behind `LLM_PROVIDER`/`LLM_BASE_URL`; ABC/factory seam in `app/infrastructure/llm/`).
- **Web frontend** still pre-Echo-Mail design (user does not want it ported).
- Smaller backend: test for `GET /v1/cards/{id}`; invalid_grant hardening in watch renewal; GCS storage; SSE.

## Conventions
- Granular conventional commits DURING work (user has insisted repeatedly), no Co-Authored-By trailer.
- Backend tests must stay green; `npx tsc --noEmit` in mobile/ before committing UI work.
- `mobile/android/` is generated (`expo prebuild`) and gitignored — never commit it.
