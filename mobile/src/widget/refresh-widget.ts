import { EmailCard, phraseOf, senderOf } from '../lib/api';
import { EchoWidget, EchoWidgetCard } from '../lib/echowidget';

let lastSignature: string | null = null;

/**
 * Push fresh data to the native StackView widget; no-op when none is placed.
 * The widget renders natively and reflects play state on its own (via the
 * shared prefs NarrationService writes), so this only needs the card data —
 * skipped when nothing material changed.
 */
export function refreshWidget(cards: EmailCard[]): void {
  const widgetCards: EchoWidgetCard[] = cards
    .filter((c) => c.processing_status === 'ready')
    .map((c) => ({
      id: c.id,
      phrase: phraseOf(c),
      sender: senderOf(c),
      tone: c.tone,
      hasAudio: c.audio_url != null,
      audioUrl: c.audio_url,
    }));

  const signature = widgetCards.map((c) => `${c.id}:${c.hasAudio}`).join('|');
  if (signature === lastSignature) return;
  lastSignature = signature;

  EchoWidget.setCards(widgetCards);
}
