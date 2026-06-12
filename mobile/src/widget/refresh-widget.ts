import React from 'react';
import { requestWidgetUpdate } from 'react-native-android-widget';

import type { EmailCard } from '../lib/api';
import { Narration } from '../lib/narration';
import { CardWidget } from './CardWidget';
import { latestReadyCard } from './widget-task-handler';

let lastSignature: string | null = null;

/**
 * Push fresh data to any placed widgets; no-op when none exist.
 * Carries the live playing state (this is the render path that runs every
 * app poll — omitting it was stomping the widget back to the play icon
 * mid-narration) and skips renders when nothing changed.
 */
export function refreshWidget(cards: EmailCard[]): void {
  const card = latestReadyCard(cards);
  const playingId = Narration.currentId();
  const signature = `${card?.id ?? 'none'}|${card?.phrase ?? ''}|${playingId ?? ''}`;
  if (signature === lastSignature) return;
  lastSignature = signature;

  requestWidgetUpdate({
    widgetName: 'EmailCard',
    renderWidget: () =>
      React.createElement(CardWidget, {
        card,
        message: card ? undefined : 'No cards yet — send yourself an email',
        playingId,
      }),
    widgetNotFound: () => {},
  }).catch(() => {});
}
