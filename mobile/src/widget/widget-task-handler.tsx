import React from 'react';
import type { WidgetTaskHandlerProps } from 'react-native-android-widget';

import { EmailCard, getCards, phraseOf, senderOf } from '../lib/api';
import { getToken } from '../lib/config';
import { CardWidget, WidgetCard } from './CardWidget';

export function toWidgetCard(card: EmailCard): WidgetCard {
  return {
    id: card.id,
    phrase: phraseOf(card),
    sender: senderOf(card),
    tone: card.tone,
    hasAudio: card.audio_url != null,
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

export async function widgetTaskHandler(props: WidgetTaskHandlerProps) {
  switch (props.widgetAction) {
    case 'WIDGET_ADDED':
    case 'WIDGET_UPDATE':
    case 'WIDGET_RESIZED': {
      const { card, message } = await fetchWidgetCard();
      props.renderWidget(<CardWidget card={card} message={message} />);
      break;
    }
    default:
      // Clicks use OPEN_URI/OPEN_APP, deletes need no cleanup.
      break;
  }
}
