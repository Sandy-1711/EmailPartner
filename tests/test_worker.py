from __future__ import annotations

import asyncio

import pytest

from app.models.db.emails import EmailProcessingStatus, Emails
from app.services.queue.worker import PipelineWorker
from app.services.storage import EmailStore

from tests.fakes import FakeImage, FakeLLM, FakeStorage
from tests.test_email_store import make_email
from tests.test_pipeline import SUMMARY, build_pipeline

pytestmark = pytest.mark.anyio


class CrashingPipeline:
    async def process(self, email: Emails) -> None:
        raise RuntimeError("boom")


async def wait_for_status(store: EmailStore, email_id, status, timeout=3.0):
    async def poll():
        while True:
            stored = await store.get_by_id(email_id)
            if stored is not None and stored.processing_status == status:
                return stored
            await asyncio.sleep(0.02)

    return await asyncio.wait_for(poll(), timeout)


async def test_worker_drains_queue_end_to_end(db_manager, app_settings):
    pipeline, store = build_pipeline(db_manager, app_settings)
    worker = PipelineWorker(db_manager, pipeline, concurrency=1, poll_interval_seconds=0.05)

    email_id, _ = await store.upsert_email(make_email())
    await worker.start()
    try:
        stored = await wait_for_status(store, email_id, EmailProcessingStatus.READY)
        assert stored.card_text is not None
    finally:
        await worker.stop()


async def test_worker_recovers_stale_jobs_on_start(db_manager, app_settings):
    pipeline, store = build_pipeline(db_manager, app_settings)
    email_id, _ = await store.upsert_email(make_email())
    # simulate a crash mid-processing: claimed but never finished, lease long expired
    claimed = await store.claim_next_pending()
    assert claimed is not None
    worker = PipelineWorker(
        db_manager, pipeline, concurrency=1, poll_interval_seconds=0.05, lease_seconds=0
    )
    await worker.start()
    try:
        await wait_for_status(store, email_id, EmailProcessingStatus.READY)
    finally:
        await worker.stop()


async def test_worker_marks_failed_when_pipeline_crashes(db_manager, app_settings):
    store = EmailStore(db_manager)
    worker = PipelineWorker(db_manager, CrashingPipeline(), concurrency=1)

    email_id, _ = await store.upsert_email(make_email())
    worked = await worker._claim_and_process_one()
    assert worked

    stored = await store.get_by_id(email_id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.FAILED
    assert stored.last_error == "boom"


async def test_worker_gives_up_after_max_attempts(db_manager, app_settings):
    store = EmailStore(db_manager)
    worker = PipelineWorker(db_manager, CrashingPipeline(), concurrency=1, max_attempts=2)

    email_id, _ = await store.upsert_email(make_email())
    for _ in range(2):
        await worker._claim_and_process_one()
        await store.requeue(email_id)

    # third claim exceeds max_attempts: marked failed without running the pipeline
    worked = await worker._claim_and_process_one()
    assert worked
    stored = await store.get_by_id(email_id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.FAILED
    assert stored.last_error is not None and "gave up" in stored.last_error
