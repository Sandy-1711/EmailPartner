from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Protocol

from app.infrastructure.db.main import DBManager
from app.models.db.emails import EmailProcessingStatus, Emails
from app.models.db.utils import utc_now
from app.services.storage import EmailStore

logger = logging.getLogger(__name__)


class EmailProcessor(Protocol):
    """The one thing the worker needs of a pipeline: turn a claimed email into
    a finished card. Depending on the interface (not EmailPipeline directly)
    keeps the worker decoupled and lets tests substitute a fake."""

    async def process(self, email: Emails) -> None: ...


class PipelineWorker:
    """Durable, Mongo-backed pipeline runner.

    The `emails` row is the job: rows in PENDING are claimed atomically
    (PENDING -> PROCESSING with a lease timestamp), so jobs survive restarts.
    On start, rows stuck in PROCESSING past their lease are requeued.
    """

    def __init__(
        self,
        db_manager: DBManager,
        pipeline: EmailProcessor,
        *,
        concurrency: int = 2,
        poll_interval_seconds: float = 15.0,
        lease_seconds: int = 600,
        max_attempts: int = 5,
    ) -> None:
        self._store = EmailStore(db_manager)
        self._pipeline = pipeline
        self._concurrency = concurrency
        self._poll_interval = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts
        self._wakeup = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []

    def notify(self) -> None:
        """Nudge the workers; safe to call from anywhere on the loop."""
        self._wakeup.set()

    async def start(self) -> None:
        requeued = await self._store.reset_stale_processing(
            utc_now() - timedelta(seconds=self._lease_seconds)
        )
        if requeued:
            logger.info("PipelineWorker: requeued %d stale jobs on startup", requeued)
        self._tasks = [
            asyncio.create_task(self._run_loop(), name=f"pipeline-worker-{i}")
            for i in range(self._concurrency)
        ]
        self._wakeup.set()

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def _run_loop(self) -> None:
        while True:
            worked = False
            try:
                worked = await self._claim_and_process_one()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("PipelineWorker: iteration failed")
            if worked:
                continue  # drain the queue before sleeping
            self._wakeup.clear()
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=self._poll_interval)
            except asyncio.TimeoutError:
                pass

    async def _claim_and_process_one(self) -> bool:
        email = await self._store.claim_next_pending()
        if email is None:
            return False
        await self._process(email)
        return True

    async def _process(self, email: Emails) -> None:
        if email.attempts > self._max_attempts:
            logger.warning(
                "PipelineWorker: giving up on %s after %d attempts",
                email.id,
                email.attempts - 1,
            )
            await self._store.update_card_fields(
                email.id,
                processing_status=EmailProcessingStatus.FAILED,
                last_error=f"gave up after {email.attempts - 1} attempts",
            )
            return
        try:
            await self._pipeline.process(email)
        except Exception as exc:
            logger.exception("PipelineWorker: pipeline crashed for %s", email.id)
            await self._store.update_card_fields(
                email.id,
                processing_status=EmailProcessingStatus.FAILED,
                last_error=str(exc) or exc.__class__.__name__,
            )
