import React from 'react';
import { FlexWidget, TextWidget } from 'react-native-android-widget';

import { makeWave } from '../components/WavePlayer';
import { paletteFor } from '../tones';

export interface WidgetCard {
  id: string;
  phrase: string;
  sender: string;
  tone: string | null;
  hasAudio: boolean;
}

/**
 * Echo Mail home-screen widget: tone gradient, the distilled phrase, and a
 * static mini waveform that deep-links into narration.
 *
 * Layout note: react-native-android-widget renders the tree to a bitmap and
 * shows it in an ImageView with scaleType="matrix" (no scaling, top-left
 * anchored). Launchers often over-report the cell size, which clips the
 * bitmap at the bottom/right — so everything sits inside a transparent
 * safety inset and the visible card keeps its corners even when clipped.
 */
export function CardWidget({ card, message }: { card: WidgetCard | null; message?: string }) {
  const palette = paletteFor(card?.tone);
  const wave = card ? makeWave(card.id, 18) : [];

  return (
    <FlexWidget
      style={{
        width: 'match_parent',
        height: 'match_parent',
        padding: 6, // safety inset: clipping eats this, not the card
      }}
    >
      <FlexWidget
        clickAction={card ? 'OPEN_URI' : 'OPEN_APP'}
        clickActionData={card ? { uri: `emailpartner://read/${card.id}` } : undefined}
        style={{
          width: 'match_parent',
          height: 'match_parent',
          borderRadius: 24,
          backgroundGradient: {
            from: palette.blobs[0],
            to: palette.base,
            orientation: 'TL_BR',
          },
          paddingHorizontal: 14,
          paddingVertical: 12,
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <FlexWidget
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            width: 'match_parent',
          }}
        >
          <FlexWidget
            style={{
              width: 7,
              height: 7,
              borderRadius: 4,
              backgroundColor: palette.dot,
              marginRight: 7,
            }}
          />
          <TextWidget
            text={palette.label.toUpperCase()}
            maxLines={1}
            style={{ fontSize: 10, color: '#ffffffeb', letterSpacing: 0.08 }}
          />
        </FlexWidget>

        <FlexWidget style={{ width: 'match_parent' }}>
          {card ? (
            <TextWidget
              text={card.sender}
              maxLines={1}
              style={{ fontSize: 11, color: '#ffffffc4', marginBottom: 3 }}
            />
          ) : null}
          <TextWidget
            text={card ? card.phrase : message ?? 'Open Echo Mail to get started'}
            maxLines={2}
            style={{
              fontSize: card ? 19 : 14,
              color: '#ffffff',
              fontWeight: 'bold',
              letterSpacing: -0.03,
            }}
          />
        </FlexWidget>

        {card && card.hasAudio ? (
          <FlexWidget
            clickAction="OPEN_URI"
            clickActionData={{ uri: `emailpartner://play/${card.id}` }}
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              width: 'match_parent',
              marginTop: 8,
            }}
          >
            <FlexWidget
              style={{
                width: 28,
                height: 28,
                borderRadius: 14,
                backgroundColor: palette.accent,
                justifyContent: 'center',
                alignItems: 'center',
                marginRight: 9,
              }}
            >
              <TextWidget text="▶" style={{ fontSize: 11, color: '#0a0612' }} />
            </FlexWidget>
            <FlexWidget style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
              {wave.map((v, i) => (
                <FlexWidget
                  key={i}
                  style={{
                    width: 3,
                    height: Math.round(6 + v * 16),
                    borderRadius: 2,
                    backgroundColor: '#ffffff4d',
                    marginRight: 3,
                  }}
                />
              ))}
            </FlexWidget>
          </FlexWidget>
        ) : null}
      </FlexWidget>
    </FlexWidget>
  );
}
