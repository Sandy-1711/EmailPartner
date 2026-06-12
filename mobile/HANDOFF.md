# Echo Mail (EmailPartner mobile) — handoff

State as of 2026-06-12. Backend feature-complete + tested; the Expo app implements the **Echo Mail design** (Claude Design handoff bundle) end-to-end and builds; remaining work is verification + the "make it real" steps below.

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

## What REMAINS

1. **Verify the Echo Mail build** — a fresh APK build was the last step (new native deps: react-native-svg, expo-font). `mobile/android/app/build/outputs/apk/debug/app-debug.apk`; install on emulator `ep_test` or the phone, check: mesh motion, fonts, detail screen, widget render, lock-screen notification during playback (lock the phone while narration plays).
   - Build env quirks (already solved, don't rediscover): `JAVA_HOME="C:\Program Files\Microsoft\jdk-17.0.10.7-hotspot"` (system JAVA_HOME is broken); AVD `ep_test` exists (created by hand-writing INI files — avdmanager breaks on JDK 17).
   - Testing without the real backend: `C:\Users\sandy\AppData\Local\Temp\mock_ep.py` (mock API on :8000 incl. fake instant sign-in). Phone via USB: `adb reverse tcp:8081 tcp:8081` (Metro) + `tcp:8000 tcp:8000` (mock), server URL `http://localhost:8000`. Debug APK needs Metro running (`npx expo start`).
2. **Run against the real backend** — Mongo + `uvicorn app.main:app` + ngrok + real Google sign-in; real TTS narration replaces the fake.wav (which makes play stop after ~5s).
3. **Release APK** (standalone, no Metro): `cd mobile/android && gradlew assembleRelease` with the JAVA_HOME above.
4. **Local model support** (user wants this eventually): add an OpenAI-compatible `LLMProvider` (Ollama/LM Studio) behind `LLM_PROVIDER`/`LLM_BASE_URL` env vars; the ABC + factory seam already exists in `app/infrastructure/llm/`.
5. **Web frontend** still has the pre-Echo-Mail design; port phrase/tone/mesh look if one design language is wanted.
6. Smaller: test for `GET /v1/cards/{id}`; invalid_grant hardening in the watch renewal loop; GCS storage; SSE.

## Conventions
- Granular conventional commits DURING work (user has insisted repeatedly), no Co-Authored-By trailer.
- Backend tests must stay green; `npx tsc --noEmit` in mobile/ before committing UI work.
- `mobile/android/` is generated (`expo prebuild`) and gitignored — never commit it.
