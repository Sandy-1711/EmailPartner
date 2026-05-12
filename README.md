# EmailPartner

Multi-user service that watches each user's Gmail and turns every new email into a "card" containing an AI-generated summary and illustration.

## How it works

1. User signs in with Google (OIDC + Gmail scopes in one consent).
2. We persist their refresh token (AES-GCM envelope encrypted) and start a Gmail `users.watch` against a Pub/Sub topic.
3. Google pushes notifications to `POST /v1/webhooks/gmail/`. The webhook syncs history via `users.history.list`, fetches each new message with `format=full`, and queues processing.
4. A background task per message: Gemini summarises the body (`headline`, `summary`, `tone`), Gemini/Imagen generates a matching illustration, both are persisted on the email row.
5. `GET /v1/cards/` returns the populated cards.

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

Open `http://localhost:8000/v1/auth/google/start` in a browser, complete consent, land on the callback. You'll receive an `ep_session` cookie; `GET /v1/auth/me` will then return your identity.

Send yourself an email. Within ~30s, `GET /v1/cards/?user_id=<your-user-id>` returns it with `processing_status=ready`, a summarized `text`, and a `background_image_url` that loads from `/static/illustrations/...`.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/v1/auth/google/start` | Returns Google OAuth URL (sign-in + Gmail in one consent) |
| GET  | `/v1/auth/google/callback` | Exchanges code, verifies id_token, creates/links user, starts Gmail watch, sets session cookie |
| GET  | `/v1/auth/me` | Returns current user (requires session cookie) |
| POST | `/v1/auth/logout` | Clears session cookie |
| POST | `/v1/auth/delete-account` | Marks user deleted |
| POST | `/v1/webhooks/gmail/` | Pub/Sub push target |
| GET  | `/v1/cards/` | Lists cards for a user |
| POST | `/v1/cards/{id}/retry` | Re-runs the pipeline for one card |
| POST | `/v1/admin/watch/renew` | Manually renew expiring watches (gated by `X-Admin-Token`) |

## Architecture notes

- **Persistence**: MongoDB. Models in `app/models/db/` use `pydantic-mongo`. Indexes set up at startup in `app/infrastructure/db/indexes.py`.
- **Secrets at rest**: Gmail refresh/access tokens stored as `EncryptedBlob` (AES-GCM envelope). Master key from `ENCRYPTION_MASTER_KEY`.
- **LLM**: `app/infrastructure/llm/` exposes a `LLMManager` with a `GeminiProvider`. The pipeline asks for a JSON-structured `SummaryResult`.
- **Image gen**: `app/infrastructure/images/` exposes `ImageManager`. `GeminiImageProvider` covers both `imagen-*` (`generate_images`) and `gemini-*-image` (`generate_content` with IMAGE modality). The model name picks the API path.
- **Storage**: `app/infrastructure/storage/` Protocol + `LocalBlobStorage` (writes to `LOCAL_STORAGE_DIR`, served from `/static/illustrations`). Swap to a GCS/S3 implementation by adding one class.
- **Async**: Pub/Sub webhook returns 200 immediately; `asyncio.create_task` runs the summary + image pipeline in-process. Single-instance only; for horizontal scale move to a queue.
- **Watch renewal**: Lifespan starts an hourly loop in `WatchRenewalService` that re-issues `users.watch` for accounts within 24h of expiration. Disable with `ENABLE_BACKGROUND_JOBS=false` (e.g. in tests).
- **Retries**: Tenacity wraps `Gmail.list_history`, `Gmail.get_message`, and `OAuthClient.refresh_access_token` (3 attempts, exponential backoff, 429/5xx + transport errors).

## Docker

```bash
docker build -t emailpartner .
docker run --rm -p 8000:8000 --env-file .env -v "$(pwd)/var:/app/var" emailpartner
```

## What's not here yet

- Audio narration (model has `card_audio_url` but it isn't generated).
- Durable queue (current `asyncio.create_task` is in-process; jobs lost on restart).
- Cloud blob storage (Local FS only; abstraction in place).
- Tests.
- A frontend.
