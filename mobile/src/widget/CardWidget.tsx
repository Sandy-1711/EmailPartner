import React from 'react';
import { FlexWidget, TextWidget } from 'react-native-android-widget';

import { paletteFor } from '../tones';

export interface WidgetCard {
  id: string;
  phrase: string;
  sender: string;
  tone: string | null;
  hasAudio: boolean;
}

/**
 * Home-screen widget: tone-tinted gradient, the email distilled to one
 * phrase, and listen/read actions that deep-link into the app.
 * (RemoteViews can't run sensors or animations — the gyro parallax version
 * of this design lives in the in-app feed.)
 */
export function CardWidget({ card, message }: { card: WidgetCard | null; message?: string }) {
  const palette = paletteFor(card?.tone);

  return (
    <FlexWidget
      clickAction="OPEN_APP"
      style={{
        width: 'match_parent',
        height: 'match_parent',
        borderRadius: 24,
        backgroundGradient: {
          from: palette.from,
          to: palette.to,
          orientation: 'TL_BR',
        },
        paddingHorizontal: 14,
        paddingVertical: 12,
        justifyContent: 'space-between',
        alignItems: 'flex-start',
      }}
    >
      <TextWidget
        text={card ? card.sender.toUpperCase() : 'EMAILPARTNER'}
        maxLines={1}
        style={{ fontSize: 9, color: palette.dim, letterSpacing: 0.15 }}
      />

      <TextWidget
        text={card ? card.phrase : message ?? 'Open the app to get started'}
        maxLines={2}
        style={{
          fontSize: card ? 17 : 13,
          color: '#ffffff',
          fontWeight: 'bold',
          marginTop: 4,
          marginBottom: 6,
        }}
      />

      {card ? (
        <FlexWidget style={{ flexDirection: 'row' }}>
          {card.hasAudio ? (
            <FlexWidget
              clickAction="OPEN_URI"
              clickActionData={{ uri: `emailpartner://play/${card.id}` }}
              style={{
                backgroundColor: '#ffffff2b',
                borderRadius: 14,
                paddingHorizontal: 11,
                paddingVertical: 5,
                marginRight: 6,
              }}
            >
              <TextWidget text="▶  Listen" style={{ fontSize: 11, color: '#ffffff' }} />
            </FlexWidget>
          ) : null}
          <FlexWidget
            clickAction="OPEN_URI"
            clickActionData={{ uri: `emailpartner://read/${card.id}` }}
            style={{
              backgroundColor: '#ffffff2b',
              borderRadius: 14,
              paddingHorizontal: 11,
              paddingVertical: 5,
            }}
          >
            <TextWidget text="👁  Read" style={{ fontSize: 11, color: '#ffffff' }} />
          </FlexWidget>
        </FlexWidget>
      ) : null}
    </FlexWidget>
  );
}
