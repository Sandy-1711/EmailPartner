from __future__ import annotations

import pytest

from app.models.db.emails import EmailProcessingStatus
from app.services.pipeline.email_pipeline import EmailPipeline, SummaryResult
from app.services.storage import EmailStore

from tests.fakes import FakeImage, FakeLLM, FakeStorage
from tests.test_email_store import make_email

pytestmark = pytest.mark.anyio


SUMMARY = SummaryResult(
    headline="Acme accepted your offer",
    summary="The contract is signed and starts Monday.",
    tone="informative",
    image_caption="Acme said yes",
    visual_concept="an envelope with falling paper confetti",
    narration="Acme accepted your offer. The contract starts Monday.",
)


def build_pipeline(db_manager, settings, llm=None, image=None, storage=None):
    return (
        EmailPipeline(
            db_manager,
            settings,
            storage or FakeStorage(),
            llm or FakeLLM(result=SUMMARY),
            image or FakeImage(),
        ),
        EmailStore(db_manager),
    )


async def claimed_email(store: EmailStore):
    await store.upsert_email(make_email())
    claimed = await store.claim_next_pending()
    assert claimed is not None
    return claimed


async def test_process_success_produces_full_card(db_manager, app_settings):
    storage = FakeStorage()
    pipeline, store = build_pipeline(db_manager, app_settings, storage=storage)
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_text == "Acme accepted your offer\n\nThe contract is signed and starts Monday."
    assert stored.card_background_url == f"mem://users/{email.user_id}/emails/{email.id}.png"
    assert stored.card_audio_url == f"mem://users/{email.user_id}/emails/{email.id}.wav"
    assert storage.blobs[f"users/{email.user_id}/emails/{email.id}.wav"][1] == "audio/wav"


async def test_summary_failure_marks_failed(db_manager, app_settings):
    pipeline, store = build_pipeline(
        db_manager, app_settings, llm=FakeLLM(summary_error=RuntimeError("quota"))
    )
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.FAILED
    assert stored.last_error is not None and "quota" in stored.last_error


async def test_illustration_failure_is_tolerated(db_manager, app_settings):
    pipeline, store = build_pipeline(
        db_manager, app_settings, image=FakeImage(error=RuntimeError("no paint"))
    )
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_background_url is None
    assert stored.card_audio_url is not None


async def test_narration_failure_is_tolerated(db_manager, app_settings):
    pipeline, store = build_pipeline(
        db_manager,
        app_settings,
        llm=FakeLLM(result=SUMMARY, tts_error=RuntimeError("no voice")),
    )
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_audio_url is None


async def test_narration_disabled_skips_tts(db_manager, app_settings):
    settings = app_settings.model_copy(update={"enable_audio_narration": False})
    llm = FakeLLM(result=SUMMARY)
    pipeline, store = build_pipeline(db_manager, settings, llm=llm)
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_audio_url is None
    assert llm.tts_calls == []
