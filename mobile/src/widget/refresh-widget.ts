import React from 'react';
import { requestWidgetUpdate } from 'react-native-android-widget';

import type { EmailCard } from '../lib/api';
import { CardWidget } from './CardWidget';
import { latestReadyCard } from './widget-task-handler';

/** Push fresh data to any placed widgets; no-op when none exist. */
export function refreshWidget(cards: EmailCard[]): void {
  const card = latestReadyCard(cards);
  requestWidgetUpdate({
    widgetName: 'EmailCard',
    renderWidget: () =>
      React.createElement(CardWidget, {
        card,
        message: card ? undefined : 'No cards yet — send yourself an email',
      }),
    widgetNotFound: () => {},
  }).catch(() => {});
}
