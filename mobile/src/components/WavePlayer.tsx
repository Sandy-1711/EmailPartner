import { Pause, Play } from 'lucide-react-native';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts } from '../theme';
import type { TonePalette } from '../tones';

/**
 * Echo Mail "listen to summary" control: accent play/pause circle + a
 * waveform that fills as it plays, pulses while playing, and scrubs by
 * touch (drag shows a scrub bar; the seek commits on release so dragging
 * stays 60fps instead of hammering the native player).
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

/**
 * Six staggered pulse values; every bar is permanently attached to one
 * (transform identity never changes — swapping or removing native-driven
 * transforms crashes Fabric's diffing). Loops run only while playing; on
 * stop, values ease back to 1. Varied durations keep it organic, not
 * uniform.
 */
const PULSE_COUNT = 6;

function usePulse(playing: boolean): Animated.Value[] {
  const values = useRef(
    Array.from({ length: PULSE_COUNT }, () => new Animated.Value(1))
  ).current;
  useEffect(() => {
    if (!playing) {
      values.forEach((v) =>
        Animated.timing(v, {
          toValue: 1,
          duration: 180,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }).start()
      );
      return;
    }
    const loops = values.map((v, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(v, {
            toValue: 1.45 - (i % 3) * 0.12,
            duration: 220 + i * 55,
            easing: Easing.inOut(Easing.sin),
            useNativeDriver: true,
          }),
          Animated.timing(v, {
            toValue: 0.66 + (i % 4) * 0.07,
            duration: 260 + ((i * 97) % 140),
            easing: Easing.inOut(Easing.sin),
            useNativeDriver: true,
          }),
          Animated.timing(v, {
            toValue: 1,
            duration: 200 + (i % 2) * 90,
            easing: Easing.inOut(Easing.sin),
            useNativeDriver: true,
          }),
        ])
      )
    );
    loops.forEach((l, i) => setTimeout(() => l.start(), i * 60));
    return () => loops.forEach((l) => l.stop());
  }, [playing, values]);
  return values;
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
  /** scrub by touch (active card only); called once, on release */
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
  const barsPageX = useRef(0);
  const barsRef = useRef<View | null>(null);
  const pulse = usePulse(playing);
  // While scrubbing, the waveform follows the finger via local state only;
  // the actual seek fires once on release.
  const [scrub, setScrub] = useState<number | null>(null);
  const shown = scrub ?? progress;

  // locationX is relative to whichever child bar the finger hits, so seek
  // math uses pageX against the container's measured window position.
  const fractionFromPageX = (pageX: number) =>
    barsWidth.current > 0
      ? Math.max(0, Math.min(1, (pageX - barsPageX.current) / barsWidth.current))
      : 0;

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
          ref={barsRef}
          style={[styles.bars, { height: barH }]}
          onLayout={(e) => {
            barsWidth.current = e.nativeEvent.layout.width;
            barsRef.current?.measureInWindow((x) => {
              barsPageX.current = x;
            });
          }}
          onStartShouldSetResponder={() => onSeek != null}
          onMoveShouldSetResponder={() => onSeek != null}
          onResponderGrant={(e) => setScrub(fractionFromPageX(e.nativeEvent.pageX))}
          onResponderMove={(e) => setScrub(fractionFromPageX(e.nativeEvent.pageX))}
          onResponderRelease={(e) => {
            const f = fractionFromPageX(e.nativeEvent.pageX);
            setScrub(null);
            onSeek?.(f);
          }}
          onResponderTerminate={() => setScrub(null)}
        >
          <View style={styles.barsInner}>
            {wave.map((v, i) => {
              const filled = i / wave.length <= shown;
              return (
                <Animated.View
                  key={i}
                  style={{
                    flex: 1,
                    height: `${v * 100}%`,
                    minWidth: 2,
                    borderRadius: 4,
                    backgroundColor: filled ? palette.accent : 'rgba(255,255,255,0.26)',
                    // node identity is constant for the bar's lifetime
                    transform: [{ scaleY: pulse[i % PULSE_COUNT] }],
                  }}
                />
              );
            })}
          </View>
          {scrub != null && (
            <View
              pointerEvents="none"
              style={[
                styles.scrubLine,
                { left: `${scrub * 100}%`, backgroundColor: palette.accent },
              ]}
            />
          )}
        </View>
      </View>

      {hero && (
        <View style={styles.times}>
          <Text style={styles.time}>{fmt(shown * duration)}</Text>
          <Text style={styles.time}>
            {scrub != null ? 'Scrubbing' : playing ? 'Now playing' : progress >= 1 ? 'Replay' : 'Summary'}
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
  bars: { flex: 1 },
  barsInner: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2.5,
    height: '100%',
  },
  scrubLine: {
    position: 'absolute',
    top: -6,
    bottom: -6,
    width: 3,
    borderRadius: 2,
    opacity: 0.95,
  },
  times: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  time: { color: 'rgba(255,255,255,0.6)', fontFamily: fonts.medium, fontSize: 12, letterSpacing: 0.2 },
});
