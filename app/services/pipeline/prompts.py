from __future__ import annotations

from app.models.db.emails import Emails

EMAIL_SUMMARY_SYSTEM = (
    "You are an assistant that distills an email into a glanceable card. "
    "Return a structured response with six fields, all in English:\n"
    "- headline: max 8 words, the core ask or news (sentence case, no end punctuation).\n"
    "- summary: 1-3 sentences in plain English, no greetings or sign-offs.\n"
    "- tone: one of informative, urgent, social, promotional, transactional — chosen from the email's content.\n"
    "- image_caption: a punchy 3-7 word line written as the assistant addressing the user in second person. "
    "State the main outcome directly: who did/sent what to the user, or what the user must do. "
    "Examples: \"Acme rejected you\", \"Your refund is on the way\", \"Sarah wants to meet Friday\", "
    "\"Action required: verify your email\". "
    "Use the actual company or person name when present. No quotes, no emoji, no end punctuation.\n"
    "- visual_concept: a short concrete English description (5-15 words) of a single foreshadowing scene "
    "that metaphorically represents the email — never literal text or logos. "
    "Examples: \"a closed wooden door in dim corridor lighting\", "
    "\"an envelope with falling paper confetti\", "
    "\"a calendar page with a circled date and a coffee cup\", "
    "\"a green checkmark stamp pressed onto a paper receipt\".\n"
    "- narration: a 1-3 sentence spoken script addressed to the user in second person, "
    "as a warm personal assistant briefing them aloud. Conversational, concrete, no markdown, "
    "no emoji, no URLs; spell out anything that would sound wrong read aloud. "
    "Example: \"Sarah from Acme wants to move your demo to Friday afternoon. "
    "She asked you to confirm by tomorrow.\"\n"
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


def build_illustration_prompt(
    *, image_caption: str, visual_concept: str, tone: str
) -> str:
    palette = _TONE_PALETTE.get(tone, _TONE_PALETTE["informative"])
    return (
        f"A 16:9 widescreen card image, cinematic composition. "
        f"Background: a soft, atmospheric illustration of {visual_concept}, "
        f"slightly out of focus, used as the scene behind a glass panel. "
        f"Palette: {palette}. "
        f"Foreground: a centered frosted glassmorphism panel — translucent, "
        f"with a soft white tint, gentle blur of the background behind it, "
        f"a thin 1px light border, subtle inner highlight, and a soft drop shadow. "
        f"On the glass panel, render the exact English text: \"{image_caption}\" "
        f"in a clean modern sans-serif, white with high contrast, perfectly legible, "
        f"horizontally centered, no quotation marks shown. "
        f"Render only this text and nothing else — no other words, no logos, "
        f"no watermarks, no UI elements, no faces of real people. "
        f"Aspect ratio strictly 16:9 (widescreen, landscape)."
    )
