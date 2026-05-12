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
