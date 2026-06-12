import { Pause, Play } from 'lucide-react-native';
import React, { useMemo, useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts } from '../theme';
import type { TonePalette } from '../tones';

/**
 * Echo Mail "listen to summary" control: accent play/pause circle + a
 * waveform that fills as it plays. The wave shape is deterministic per
 * email id so it never reflows between renders (ported from the design).
 */

function seedFrom(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 233280;
  return h + 3;
}

export function makeWave(id: string, n = 44): number[] {
  const out: number[] = [];
  let s = seedFrom(id) * 9301 + 49297;
  for (let i = 0; i < n; i++) {
    s = (s * 9301 + 49297) % 233280;
    const r = s / 233280;
    const env = 0.55 + 0.45 * Math.sin((i / n) * Math.PI);
    out.push(Math.max(0.18, Math.min(1, env * (0.45 + r * 0.7))));
  }
  return out;
}

function fmt(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

interface Props {
  emailId: string;
  palette: TonePalette;
  playing: boolean;
  /** 0..1 */
  progress: number;
  /** seconds; 0 when unknown */
  duration: number;
  onToggle: () => void;
  /** press-in hint so the stream buffers before the tap completes */
  onPreload?: () => void;
  /** scrub by tapping/dragging the waveform (active card only) */
  onSeek?: (fraction: number) => void;
  size?: 'hero' | 'mini';
}

export function WavePlayer({
  emailId,
  palette,
  playing,
  progress,
  duration,
  onToggle,
  onPreload,
  onSeek,
  size = 'hero',
}: Props) {
  const wave = useMemo(() => makeWave(emailId, size === 'hero' ? 44 : 34), [emailId, size]);
  const hero = size === 'hero';
  const btn = hero ? 60 : 42;
  const barH = hero ? 52 : 28;
  const barsWidth = useRef(0);

  const seekFromX = (x: number) => {
    if (onSeek && barsWidth.current > 0) {
      onSeek(x / barsWidth.current);
    }
  };

  return (
    <View style={{ width: '100%' }}>
      <View style={[styles.row, { gap: hero ? 16 : 11 }]}>
        <Pressable
          onPress={onToggle}
          onPressIn={onPreload}
          style={({ pressed }) => [
            styles.button,
            {
              width: btn,
              height: btn,
              borderRadius: btn / 2,
              backgroundColor: palette.accent,
              transform: [{ scale: pressed ? 0.94 : 1 }],
            },
          ]}
        >
          {playing ? (
            <Pause size={hero ? 24 : 17} color="#0a0612" fill="#0a0612" strokeWidth={0} />
          ) : (
            <Play
              size={hero ? 24 : 17}
              color="#0a0612"
              fill="#0a0612"
              strokeWidth={0}
              style={{ marginLeft: hero ? 3 : 2 }}
            />
          )}
        </Pressable>

        <View
          style={[styles.bars, { height: barH }]}
          onLayout={(e) => {
            barsWidth.current = e.nativeEvent.layout.width;
          }}
          onStartShouldSetResponder={() => onSeek != null}
          onMoveShouldSetResponder={() => onSeek != null}
          onResponderGrant={(e) => seekFromX(e.nativeEvent.locationX)}
          onResponderMove={(e) => seekFromX(e.nativeEvent.locationX)}
        >
          {wave.map((v, i) => {
            const filled = i / wave.length <= progress;
            return (
              <View
                key={i}
                style={{
                  flex: 1,
                  height: `${v * 100}%`,
                  minWidth: 2,
                  borderRadius: 4,
                  backgroundColor: filled ? palette.accent : 'rgba(255,255,255,0.26)',
                }}
              />
            );
          })}
        </View>
      </View>

      {hero && (
        <View style={styles.times}>
          <Text style={styles.time}>{fmt(progress * duration)}</Text>
          <Text style={styles.time}>
            {playing ? 'Now playing' : progress >= 1 ? 'Replay' : 'Summary'}
          </Text>
          <Text style={styles.time}>{duration > 0 ? fmt(duration) : '–:––'}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', width: '100%' },
  button: {
    flexShrink: 0,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 8 },
  },
  bars: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 2.5 },
  times: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  time: { color: 'rgba(255,255,255,0.6)', fontFamily: fonts.medium, fontSize: 12, letterSpacing: 0.2 },
});
