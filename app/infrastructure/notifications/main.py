from __future__ import annotations

import logging

from httpx import AsyncClient

from app.infrastructure.notifications.providers import FcmSender, PushSender

logger = logging.getLogger(__name__)


def build_push_sender(
    *, credentials_file: str | None, http_client: AsyncClient
) -> PushSender | None:
    """Build the push sender, or None when push is disabled (no credentials).

    Selection is by configuration rather than a provider name: today the only
    transport is FCM, picked up when a Firebase service-account file is set.
    """
    if not credentials_file:
        return None
    try:
        sender = FcmSender.from_credentials_file(credentials_file, http_client)
    except Exception:
        logger.exception(
            "build_push_sender: could not load credentials from %s; push disabled",
            credentials_file,
        )
        return None
    logger.info("FCM push enabled")
    return sender
