from __future__ import annotations

from app.models.db.emails import Emails


EMAIL_SUMMARY_SYSTEM = (
    "You are an assistant that distills an email into a short card. "
    "Return a structured response with three fields: "
    "headline (max 8 words capturing the core ask or news), "
    "summary (1-3 sentences in plain English, no greetings or sign-offs), "
    "and tone (one of: informative, urgent, social, promotional, transactional). "
    "Ignore signatures, legal disclaimers, and unsubscribe footers."
)


def build_summary_prompt(email: Emails, max_body_chars: int) -> str:
    body = (email.body or email.snippet or "").strip()
    if len(body) > max_body_chars:
        body = body[:max_body_chars] + "\n[...truncated]"
    return (
        f"Subject: {email.subject or '(no subject)'}\n"
        f"From: {email.from_email or '(unknown)'}\n"
        f"\n"
        f"{body or '(empty body)'}"
    )


_TONE_PALETTE = {
    "informative": "calm muted blues and greys, soft daylight",
    "urgent": "warm reds and oranges, high contrast",
    "social": "warm pastels, soft pinks and yellows",
    "promotional": "vibrant saturated colors, playful gradients",
    "transactional": "neutral greens and beiges, clean and precise",
}


def build_illustration_prompt(*, headline: str, tone: str) -> str:
    palette = _TONE_PALETTE.get(tone, _TONE_PALETTE["informative"])
    return (
        f"Flat editorial illustration evoking: {headline}. "
        f"Style: soft shapes, gentle shading, minimal detail. "
        f"Palette: {palette}. "
        f"No text, no logos, no faces, no watermarks. "
        f"Square composition, balanced negative space."
    )
