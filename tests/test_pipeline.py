from __future__ import annotations

import pytest

from app.models.db.emails import EmailProcessingStatus
from app.services.memory import EmailMemory
from app.services.pipeline.email_pipeline import EmailPipeline, SummaryResult
from app.services.storage import EmailStore
from tests.fakes import FakeEmbedder, FakeImage, FakeLLM, FakeStorage, FakeVectorStore
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


def build_pipeline(
    db_manager, settings, llm=None, image=None, storage=None, notifier=None, memory=None
):
    return (
        EmailPipeline(
            db_manager,
            settings,
            storage or FakeStorage(),
            llm or FakeLLM(result=SUMMARY),
            image or FakeImage(),
            notifier=notifier,
            memory=memory,
        ),
        EmailStore(db_manager),
    )


class _RecordingNotifier:
    def __init__(self, error=None) -> None:
        self.error = error
        self.calls: list[dict] = []

    async def notify_card_ready(self, **kwargs) -> None:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error


async def claimed_email(store: EmailStore):
    await store.upsert_email(make_email())
    claimed = await store.claim_next_pending()
    assert claimed is not None
    return claimed


async def test_process_success_produces_full_card(db_manager, app_settings):
    storage = FakeStorage()
    settings = app_settings.model_copy(update={"enable_image_generation": True})
    pipeline, store = build_pipeline(db_manager, settings, storage=storage)
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_text == "Acme accepted your offer\n\nThe contract is signed and starts Monday."
    assert stored.card_phrase == "Acme said yes"
    assert stored.card_tone == "informative"
    assert stored.card_background_url == f"mem://users/{email.user_id}/emails/{email.id}.png"
    assert stored.card_audio_url == f"mem://users/{email.user_id}/emails/{email.id}.wav"
    assert storage.blobs[f"users/{email.user_id}/emails/{email.id}.wav"][1] == "audio/wav"


async def test_image_generation_disabled_by_default(db_manager, app_settings):
    image = FakeImage()
    pipeline, store = build_pipeline(db_manager, app_settings, image=image)
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_background_url is None
    assert image.calls == []  # the provider is never invoked when disabled


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
    settings = app_settings.model_copy(update={"enable_image_generation": True})
    pipeline, store = build_pipeline(
        db_manager, settings, image=FakeImage(error=RuntimeError("no paint"))
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


async def test_ready_pushes_notification(db_manager, app_settings):
    notifier = _RecordingNotifier()
    pipeline, store = build_pipeline(db_manager, app_settings, notifier=notifier)
    email = await claimed_email(store)

    await pipeline.process(email)

    assert len(notifier.calls) == 1
    call = notifier.calls[0]
    assert call["card_id"] == str(email.id)
    assert call["phrase"] == "Acme said yes"
    assert call["tone"] == "informative"
    assert call["audio_url"] == f"mem://users/{email.user_id}/emails/{email.id}.wav"


async def test_ready_indexes_into_memory(db_manager, app_settings):
    store = FakeVectorStore()
    memory = EmailMemory(db_manager, FakeEmbedder(), store)
    pipeline, email_store = build_pipeline(db_manager, app_settings, memory=memory)
    email = await claimed_email(email_store)

    await pipeline.process(email)

    assert str(email.id) in store.records
    assert store.records[str(email.id)].payload["user_id"] == str(email.user_id)


async def test_push_failure_does_not_fail_card(db_manager, app_settings):
    notifier = _RecordingNotifier(error=RuntimeError("fcm down"))
    pipeline, store = build_pipeline(db_manager, app_settings, notifier=notifier)
    email = await claimed_email(store)

    await pipeline.process(email)

    stored = await store.get_by_id(email.id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY


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
