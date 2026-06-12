import React from 'react';
import type { WidgetTaskHandlerProps } from 'react-native-android-widget';

import { EmailCard, getCards, phraseOf, senderOf } from '../lib/api';
import { getToken } from '../lib/config';
import { Narration } from '../lib/narration';
import { CardWidget, WidgetCard } from './CardWidget';

export function toWidgetCard(card: EmailCard): WidgetCard {
  return {
    id: card.id,
    phrase: phraseOf(card),
    sender: senderOf(card),
    tone: card.tone,
    hasAudio: card.audio_url != null,
    audioUrl: card.audio_url,
  };
}

export function latestReadyCard(cards: EmailCard[]): WidgetCard | null {
  const ready = cards.find((card) => card.processing_status === 'ready');
  return ready ? toWidgetCard(ready) : null;
}

async function fetchWidgetCard(): Promise<{ card: WidgetCard | null; message?: string }> {
  const token = await getToken();
  if (!token) {
    return { card: null, message: 'Sign in to see your cards' };
  }
  try {
    const data = await getCards(10);
    const card = latestReadyCard(data.items);
    return card
      ? { card }
      : { card: null, message: 'No cards yet — send yourself an email' };
  } catch {
    return { card: null, message: 'Open the app to refresh' };
  }
}

/**
 * Widget playback runs in the native NarrationService (modules/narration):
 * started synchronously inside the widget tap's background-FGS allowance,
 * with its own MediaSession (lock-screen controls). The JS context here can
 * die freely — toggle state lives in the native process.
 */
function toggleNarration(data: Record<string, unknown>): void {
  const id = typeof data.id === 'string' ? data.id : null;
  const audioUrl = typeof data.audioUrl === 'string' ? data.audioUrl : null;
  if (!id || !audioUrl) return;

  if (Narration.currentId() === id) {
    Narration.stop();
    return;
  }
  Narration.play(
    id,
    audioUrl,
    typeof data.phrase === 'string' ? data.phrase : 'Email summary',
    typeof data.sender === 'string' ? data.sender : ''
  );
}

export async function widgetTaskHandler(props: WidgetTaskHandlerProps) {
  switch (props.widgetAction) {
    case 'WIDGET_ADDED':
    case 'WIDGET_UPDATE':
    case 'WIDGET_RESIZED': {
      const { card, message } = await fetchWidgetCard();
      props.renderWidget(
        <CardWidget card={card} message={message} playingId={Narration.currentId()} />
      );
      break;
    }
    case 'WIDGET_CLICK': {
      if (props.clickAction === 'PLAY_NARRATION' && props.clickActionData) {
        // synchronously, before any await: stay inside the FGS allowance window
        toggleNarration(props.clickActionData);
        const { card, message } = await fetchWidgetCard();
        props.renderWidget(
          <CardWidget card={card} message={message} playingId={Narration.currentId()} />
        );
      }
      break;
    }
    default:
      break;
  }
}
