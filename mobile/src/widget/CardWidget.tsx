import React from 'react';
import {
  FlexWidget,
  ImageWidget,
  OverlapWidget,
  TextWidget,
} from 'react-native-android-widget';

import { makeWave } from '../components/WavePlayer';
import { paletteFor } from '../tones';

export interface WidgetCard {
  id: string;
  phrase: string;
  sender: string;
  tone: string | null;
  hasAudio: boolean;
  audioUrl: string | null;
}

// RemoteViews can't render gradients or SVG, so the mesh backgrounds are
// pre-rendered bitmaps (assets/mesh/, generated to match src/tones.ts).
const MESH_BG: Record<string, number> = {
  urgent: require('../../assets/mesh/widget-urgent.png'),
  social: require('../../assets/mesh/widget-social.png'),
  informative: require('../../assets/mesh/widget-informative.png'),
  transactional: require('../../assets/mesh/widget-transactional.png'),
  promotional: require('../../assets/mesh/widget-promotional.png'),
};

const WIDGET_W = 320;
const WIDGET_H = 150;

/**
 * Echo Mail home-screen widget: pre-rendered mesh, glowing dot + label,
 * the distilled phrase, and a mini waveform that plays narration headlessly
 * (the app never opens). 6dp transparent inset absorbs launcher clipping.
 */
export function CardWidget({
  card,
  message,
  playingId,
}: {
  card: WidgetCard | null;
  message?: string;
  playingId?: string | null;
}) {
  const palette = paletteFor(card?.tone);
  const wave = card ? makeWave(card.id, 16) : [];
  const playing = card != null && playingId === card.id;
  const mesh = MESH_BG[card?.tone ?? 'informative'] ?? MESH_BG.informative;

  return (
    <FlexWidget
      style={{
        width: 'match_parent',
        height: 'match_parent',
        padding: 6, // safety inset: launcher over-reports clip this, not the card
      }}
    >
      <OverlapWidget style={{ width: 'match_parent', height: 'match_parent' }}>
        <ImageWidget
          image={mesh}
          imageWidth={WIDGET_W}
          imageHeight={WIDGET_H}
          radius={24}
          clickAction={card ? 'OPEN_URI' : 'OPEN_APP'}
          clickActionData={card ? { uri: `emailpartner://read/${card.id}` } : undefined}
        />
        <FlexWidget
          style={{
            width: 'match_parent',
            height: 'match_parent',
            paddingHorizontal: 14,
            paddingVertical: 12,
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <FlexWidget style={{ flexDirection: 'row', alignItems: 'center' }}>
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
              // Plays in the app process headlessly; tap again to stop.
              clickAction="PLAY_NARRATION"
              clickActionData={{
                id: card.id,
                audioUrl: card.audioUrl,
                phrase: card.phrase,
                sender: card.sender,
              }}
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                marginTop: 8,
                backgroundColor: '#00000042',
                borderRadius: 17,
                paddingHorizontal: 10,
                paddingVertical: 5,
              }}
            >
              <FlexWidget
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 12,
                  backgroundColor: palette.accent,
                  justifyContent: 'center',
                  alignItems: 'center',
                  marginRight: 8,
                }}
              >
                <TextWidget
                  text={playing ? '◼' : '▶'}
                  style={{ fontSize: playing ? 9 : 10, color: '#0a0612' }}
                />
              </FlexWidget>
              {wave.map((v, i) => (
                <FlexWidget
                  key={i}
                  style={{
                    width: 3,
                    height: Math.round(5 + v * 13),
                    borderRadius: 2,
                    backgroundColor: playing ? palette.accent : '#ffffff59',
                    marginRight: 3,
                  }}
                />
              ))}
            </FlexWidget>
          ) : null}
        </FlexWidget>
      </OverlapWidget>
    </FlexWidget>
  );
}
