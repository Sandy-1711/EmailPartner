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

// Pre-rendered mesh backgrounds (assets/mesh/, generated to match tones.ts).
const MESH_BG: Record<string, number> = {
  urgent: require('../../assets/mesh/widget-urgent.png'),
  social: require('../../assets/mesh/widget-social.png'),
  informative: require('../../assets/mesh/widget-informative.png'),
  transactional: require('../../assets/mesh/widget-transactional.png'),
  promotional: require('../../assets/mesh/widget-promotional.png'),
};

const MESH_W = 320;
const MESH_H = 150;

/**
 * Echo Mail home-screen widget, layered for resilience: a gradient base
 * that can't fail, the mesh bitmap above it as enhancement (debug builds
 * load it via Metro — if that fails only the texture is lost, never the
 * card), and content on top. Play/stop runs in the native NarrationService
 * (the app never opens); the click handler re-renders instantly from the
 * click payload.
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
        {/* base: gradient card that always renders */}
        <FlexWidget
          style={{
            width: 'match_parent',
            height: 'match_parent',
            borderRadius: 24,
            backgroundGradient: {
              from: palette.blobs[1],
              to: palette.base,
              orientation: 'TL_BR',
            },
          }}
        />
        {/* enhancement: the real mesh texture */}
        <ImageWidget image={mesh} imageWidth={MESH_W} imageHeight={MESH_H} radius={24} />
        {/* content */}
        <FlexWidget
          clickAction={card ? 'OPEN_URI' : 'OPEN_APP'}
          clickActionData={card ? { uri: `emailpartner://read/${card.id}` } : undefined}
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
              tone: card.tone,
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
                text={playing ? '■' : '▶'}
                style={{ fontSize: playing ? 9 : 11, color: '#0a0612' }}
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
