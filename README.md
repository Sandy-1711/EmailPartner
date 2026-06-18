# EmailPartner

Multi-user service that watches each user's Gmail and turns every new email into a "card": an AI-written headline and summary, a matching illustration, and a voice narration — shown live in a web feed.

## How it works

1. User signs in with Google (OIDC + Gmail scopes in one consent) from the frontend at `/`.
2. We persist their refresh token (AES-GCM envelope encrypted) and start a Gmail `users.watch` against a Pub/Sub topic.
3. Google pushes notifications to `POST /v1/webhooks/gmail/`. The webhook syncs history via `users.history.list`, fetches each new message with `format=full`, and enqueues it (the email row in PENDING *is* the job).
4. A durable worker claims pending rows: Gemini summarises the body (`headline`, `summary`, `tone`, `narration`), Gemini/Imagen paints a matching illustration, Gemini TTS reads the narration aloud — all persisted on the email row. Jobs survive restarts via a lease sweep.
5. The frontend polls `GET /v1/cards/` and cards materialise in the feed as they finish.

## Quickstart (local)

Prereqs: Python 3.12, MongoDB running locally, a Google Cloud project with the Gmail API enabled and a Pub/Sub topic, a Gemini API key, and `ngrok` (or equivalent) so Pub/Sub can reach your laptop.

```bash
python -m venv .venv
. .venv/Scripts/activate     # PowerShell: . .venv\Scripts\Activate.ps1
pip install -r req.txt

cp .env.example .env
# Fill in OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, GMAIL_WATCH_TOPIC,
# MONGO_URI, ENCRYPTION_MASTER_KEY, OAUTH_STATE_SECRET, SESSION_SECRET,
# GEMINI_API_KEY. Generate the three secrets with:
#   python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"  # ENCRYPTION_MASTER_KEY
#   python -c "import secrets; print(secrets.token_urlsafe(48))"                    # OAUTH_STATE_SECRET, SESSION_SECRET

uvicorn app.main:app --reload
```

In another shell, expose port 8000 publicly (e.g. `ngrok http 8000`) and point your Pub/Sub push subscription at:

```
https://<your-public-host>/v1/webhooks/gmail/?token=<PUBSUB_VERIFICATION_TOKEN>
```

(The `token` query parameter is only checked if `PUBSUB_VERIFICATION_TOKEN` is set.)

### Sign in

Open `http://localhost:8000/` in a browser and click **Sign in with Google**. After consent you land back on the feed with an `ep_session` cookie set.

Send yourself an email. Within ~30s a card appears in the feed: it shimmers while the pipeline paints it, then flips to the finished illustration with a play button for the narration.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET  | `/` | Live card feed frontend |
| GET  | `/v1/auth/google/start` | Returns Google OAuth URL (sign-in + Gmail in one consent) |
| GET  | `/v1/auth/google/callback` | Exchanges code, verifies id_token, creates/links user, starts Gmail watch, sets session cookie, redirects to `/` |
| GET  | `/v1/auth/me` | Returns current user (requires session cookie) |
| POST | `/v1/auth/logout` | Clears session cookie |
| POST | `/v1/auth/delete-account` | Marks user deleted |
| POST | `/v1/webhooks/gmail/` | Pub/Sub push target |
| GET  | `/v1/cards/` | Lists cards (session cookie, or explicit `?user_id=`) |
| POST | `/v1/cards/{id}/retry` | Requeues one card through the worker |
| POST | `/v1/admin/watch/renew` | Manually renew expiring watches (gated by `X-Admin-Token`) |

## Architecture notes

- **Persistence**: MongoDB. Models in `app/models/db/` use `pydantic-mongo`. Indexes set up at startup in `app/infrastructure/db/indexes.py`.
- **Secrets at rest**: Gmail refresh/access tokens stored as `EncryptedBlob` (AES-GCM envelope). Master key from `ENCRYPTION_MASTER_KEY`.
- **LLM**: `app/infrastructure/llm/` exposes a `LLMManager` with a `GeminiProvider`. The pipeline asks for a JSON-structured `SummaryResult`. Default model: `gemini-3.1-flash-lite` (overridable via `SUMMARY_MODEL`).
- **Image gen**: `app/infrastructure/images/` exposes `ImageManager`. `GeminiImageProvider` covers both `imagen-*` (`generate_images`) and `gemini-*-image*` (`generate_content` with IMAGE+TEXT modalities). **Off by default** (`ENABLE_IMAGE_GENERATION=false`) — the mobile app renders a procedural mesh, not the illustration, so generating it just burns credits. Flip the flag to revive it; the model name picks the API path (default `gemini-2.5-flash-image`, override `IMAGE_MODEL`).
- **Audio**: `LLMProvider.synthesize_speech` renders the summary's `narration` script via Gemini TTS (default `gemini-2.5-flash-preview-tts`, voice `Kore`; override with `TTS_MODEL`/`TTS_VOICE`, disable with `ENABLE_AUDIO_NARRATION=false`). Raw PCM is wrapped as WAV and stored next to the illustration.
- **Storage**: `app/infrastructure/storage/` Protocol + `LocalBlobStorage` (writes to `LOCAL_STORAGE_DIR`, served from `/static/illustrations`). Swap to a GCS/S3 implementation by adding one class.
- **Durable queue**: the webhook only upserts email rows as PENDING and nudges `PipelineWorker` (`app/services/queue/worker.py`). Workers claim rows atomically (`find_one_and_update`, attempts + lease timestamp) and the startup sweep requeues PROCESSING rows whose lease expired — so in-flight jobs survive restarts. Tune with `PIPELINE_CONCURRENCY`, `PIPELINE_POLL_INTERVAL_SECONDS`, `PIPELINE_LEASE_SECONDS`, `PIPELINE_MAX_ATTEMPTS`. Multiple app instances can share the queue; claims are atomic.
- **Client**: mobile-only (Expo app in `mobile/`). There is no web frontend; `/` returns a JSON status. The app reads `/v1/cards/` and gets live updates via SSE at `GET /v1/cards/stream` (`CardEventBus`) plus FCM push (`POST /v1/devices` registers a token; sender in `app/infrastructure/notifications/`, gated on `FIREBASE_CREDENTIALS_FILE`).
- **Watch renewal**: Lifespan starts an hourly loop in `WatchRenewalService` that re-issues `users.watch` for accounts within 24h of expiration. On `invalid_grant` (user revoked access) the account is marked DISABLED so it stops being retried. Disable the loop with `ENABLE_BACKGROUND_JOBS=false` (e.g. in tests).
- **Retries**: Tenacity wraps `Gmail.list_history`, `Gmail.get_message`, and `OAuthClient.refresh_access_token` (3 attempts, exponential backoff, 429/5xx + transport errors).

## Docker

```bash
docker build -t emailpartner .
docker run --rm -p 8000:8000 --env-file .env -v "$(pwd)/var:/app/var" emailpartner
```

## Tests

```bash
pip install -r req-dev.txt
pytest
```

Unit tests run against an in-memory `DocumentDBManager` fake — no Mongo or network needed. Covered: queue claim/lease/requeue semantics, pipeline failure modes (summary/image/TTS), crypto envelope roundtrip, session signing, WAV packaging.

## Mobile app — Echo Mail (Android, `mobile/`)

Expo (SDK 56) React Native app implementing the **Echo Mail** design (from a Claude Design handoff): every email distilled to one phrase on a moving indigo/violet mesh gradient, with a waveform narration player. Space Grotesk type, Lucide icons, tone-driven palettes (urgent reads magenta, social reads teal — never orange).

```bash
cd mobile
npm install
npx expo prebuild --platform android   # generates android/ (gitignored)
npx expo run:android                   # build + install on device/emulator
# or just the APK: cd android && ./gradlew assembleDebug
```

- **Screens**: Inbox (tone cards, gyro-parallax mesh), Detail (hero waveform player, "The gist", expandable full email), Sign-in. A Tweaks sheet (sliders button in the header) adjusts hue, motion, font size, density — persisted on-device.
- **Audio**: one shared player; narration registers lock-screen media controls (phrase as title, sender as artist) and routes to the speaker. Playback survives backgrounding.
- **Widget**: tone-gradient card with the phrase and a mini waveform. The play button starts narration headlessly — the app never opens. Updates whenever the app fetches plus Android's 30-minute cycle.
- **Sign-in**: system browser at `/v1/auth/google/start?client=mobile`; the callback deep-links the session token back via `emailpartner://auth?token=…` (SecureStore, sent as `Authorization: Bearer`).
- Server URL is configurable on the sign-in screen — `http://10.0.2.2:8000` reaches your laptop from the emulator; ngrok HTTPS on a real phone.

## What's not here yet

- Cloud blob storage (Local FS only; abstraction in place).
- Push updates to the frontend (currently 4s polling; SSE would be the next step).
- iOS app (the Expo code is portable, but the widget is Android-only and sign-in/scheme config would need an iOS pass).
