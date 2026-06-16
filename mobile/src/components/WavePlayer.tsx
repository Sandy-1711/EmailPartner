import { Pause, Play } from 'lucide-react-native';
import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useDerivedValue,
  useSharedValue,
} from 'react-native-reanimated';

import { fonts } from '../theme';
import type { TonePalette } from '../tones';

/**
 * Echo Mail "listen to summary" control: accent play/pause circle + a
 * waveform that fills as it plays and scrubs by touch. The scrub now runs on
 * the UI thread (gesture-handler Pan + reanimated): the fill and scrub line
 * follow the finger off the JS thread, and the actual seek commits on release
 * so dragging never hammers the native player.
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

/** One row of waveform bars. Memoized so the 4Hz progress re-render (which
 *  only moves the UI-thread fill width + the time text) never remounts them. */
const WaveBars = React.memo(function WaveBars({
  wave,
  color,
  w,
}: {
  wave: number[];
  color: string;
  w: number | '100%';
}) {
  return (
    <View style={[styles.barsInner, { width: w }]}>
      {wave.map((v, i) => (
        <View
          key={i}
          style={{
            flex: 1,
            height: `${v * 100}%`,
            minWidth: 2,
            borderRadius: 4,
            backgroundColor: color,
          }}
        />
      ))}
    </View>
  );
});

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
  const [barsW, setBarsW] = useState(0);

  // playback progress mirrored into a shared value so the fill tracks it on the
  // UI thread; while scrubbing, the finger position takes over.
  const progressSV = useSharedValue(progress);
  progressSV.value = progress;
  const scrubX = useSharedValue(0);
  const scrubbing = useSharedValue(0);
  const shown = useDerivedValue(() =>
    scrubbing.value ? scrubX.value : progressSV.value
  );

  // a JS mirror of the scrub fraction, only for the time label (cheap text
  // re-render; the bars/line don't depend on it)
  const [scrubFrac, setScrubFrac] = useState<number | null>(null);

  const commitSeek = (f: number) => {
    onSeek?.(f);
    setScrubFrac(null);
  };

  const pan = Gesture.Pan()
    .enabled(onSeek != null)
    .minDistance(0)
    .onBegin((e) => {
      if (barsW <= 0) return;
      const f = Math.max(0, Math.min(1, e.x / barsW));
      scrubbing.value = 1;
      scrubX.value = f;
      runOnJS(setScrubFrac)(f);
    })
    .onUpdate((e) => {
      if (barsW <= 0) return;
      const f = Math.max(0, Math.min(1, e.x / barsW));
      scrubX.value = f;
      runOnJS(setScrubFrac)(f);
    })
    .onFinalize(() => {
      const f = scrubX.value;
      scrubbing.value = 0;
      runOnJS(commitSeek)(f);
    });

  const filledStyle = useAnimatedStyle(() => ({ width: shown.value * barsW }));
  const lineStyle = useAnimatedStyle(() => ({
    opacity: scrubbing.value,
    transform: [{ translateX: shown.value * barsW }],
  }));

  const displayed = scrubFrac ?? progress;

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

        <GestureDetector gesture={pan}>
          <View
            style={[styles.bars, { height: barH }]}
            onLayout={(e) => setBarsW(e.nativeEvent.layout.width)}
          >
            {/* base: unfilled bars */}
            <WaveBars wave={wave} color="rgba(255,255,255,0.26)" w="100%" />
            {/* fill: same bars in accent, clipped to the played/scrubbed width */}
            <Animated.View
              pointerEvents="none"
              style={[styles.fill, filledStyle]}
            >
              <WaveBars wave={wave} color={palette.accent} w={barsW} />
            </Animated.View>
            {/* scrub line, visible only while dragging */}
            <Animated.View
              pointerEvents="none"
              style={[styles.scrubLine, { backgroundColor: palette.accent }, lineStyle]}
            />
          </View>
        </GestureDetector>
      </View>

      {hero && (
        <View style={styles.times}>
          <Text style={styles.time}>{fmt(displayed * duration)}</Text>
          <Text style={styles.time}>
            {scrubFrac != null ? 'Scrubbing' : playing ? 'Now playing' : progress >= 1 ? 'Replay' : 'Summary'}
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
  bars: { flex: 1, justifyContent: 'center' },
  barsInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2.5,
    height: '100%',
  },
  // clips the accent bars to the played width; inner row keeps full width so
  // bars line up pixel-for-pixel with the base layer.
  fill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    overflow: 'hidden',
  },
  scrubLine: {
    position: 'absolute',
    top: -6,
    bottom: -6,
    left: 0,
    width: 3,
    borderRadius: 2,
  },
  times: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  time: { color: 'rgba(255,255,255,0.6)', fontFamily: fonts.medium, fontSize: 12, letterSpacing: 0.2 },
});
