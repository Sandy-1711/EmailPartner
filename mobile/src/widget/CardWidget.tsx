import React from 'react';
import {
  FlexWidget,
  OverlapWidget,
  SvgWidget,
  TextWidget,
} from 'react-native-android-widget';

import { makeWave } from '../components/WavePlayer';
import { paletteFor } from '../tones';
import { meshSvg } from './meshSvg';

export interface WidgetCard {
  id: string;
  phrase: string;
  sender: string;
  tone: string | null;
  hasAudio: boolean;
  audioUrl: string | null;
}

/**
 * Echo Mail home-screen widget, layered for resilience: a gradient base
 * that can't fail, the mesh texture above it as an inline SVG string
 * (rendered natively by AndroidSVG — no Metro, so it shows in debug AND
 * release, unlike the old require()'d PNGs), and content on top. Play/stop
 * runs in the native NarrationService (the app never opens); the click
 * handler re-renders instantly from the click payload.
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
  const wave = card ? makeWave(card.id, 9) : [];
  const playing = card != null && playingId === card.id;

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
        {/* enhancement: the mesh texture, drawn natively from an SVG string */}
        <SvgWidget
          svg={meshSvg(palette)}
          style={{ width: 'match_parent', height: 'match_parent' }}
        />
        {/* content — mirrors the in-app ToneCard: dot+sender header, phrase
            hero, then a play pill + waveform footer */}
        <FlexWidget
          clickAction={card ? 'OPEN_URI' : 'OPEN_APP'}
          clickActionData={card ? { uri: `emailpartner://read/${card.id}` } : undefined}
          style={{
            width: 'match_parent',
            height: 'match_parent',
            paddingHorizontal: 16,
            paddingVertical: 14,
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
        <FlexWidget style={{ flexDirection: 'row', alignItems: 'center' }}>
          {/* tone dot with a faux-glow halo (widgets can't render shadows) */}
          <FlexWidget
            style={{
              width: 14,
              height: 14,
              borderRadius: 7,
              backgroundColor: `${palette.dot}40`,
              justifyContent: 'center',
              alignItems: 'center',
              marginRight: 8,
            }}
          >
            <FlexWidget
              style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: palette.dot }}
            />
          </FlexWidget>
          <TextWidget
            text={(card ? card.sender : 'ECHO MAIL').toUpperCase()}
            maxLines={1}
            style={{ fontSize: 11, color: '#ffffffe6', letterSpacing: 0.06, fontWeight: '600' }}
          />
        </FlexWidget>

        <TextWidget
          text={card ? card.phrase : message ?? 'Open Echo Mail to get started'}
          maxLines={2}
          style={{
            fontSize: card ? 21 : 15,
            color: '#ffffff',
            fontWeight: 'bold',
            letterSpacing: -0.4,
          }}
        />

        {card && card.hasAudio ? (
          <FlexWidget style={{ flexDirection: 'row', alignItems: 'center' }}>
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
                backgroundColor: '#00000047',
                borderRadius: 999,
                paddingLeft: 5,
                paddingRight: 12,
                paddingVertical: 5,
                marginRight: 10,
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
              <TextWidget
                text={playing ? 'Playing' : 'Listen'}
                maxLines={1}
                style={{ fontSize: 12, color: '#ffffff', fontWeight: '600' }}
              />
            </FlexWidget>
            {wave.map((v, i) => (
              <FlexWidget
                key={i}
                style={{
                  width: 3,
                  height: Math.round(5 + v * 14),
                  borderRadius: 2,
                  backgroundColor: playing ? palette.accent : '#ffffff4d',
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
