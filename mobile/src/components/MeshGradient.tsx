import {
  Blur,
  Canvas,
  Circle,
  Group,
  LinearGradient,
  RadialGradient,
  Rect,
  vec,
} from '@shopify/react-native-skia';
import React, { useEffect, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';
import {
  cancelAnimation,
  Easing,
  useDerivedValue,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import type { Tilt } from '../hooks/useTilt';
import type { TonePalette } from '../tones';

/**
 * Echo Mail mesh gradient on a real Skia canvas: colored blobs drifting under
 * a TRUE gaussian blur (a Skia Blur image filter over the whole blob group),
 * not the layered react-native-svg radial stops that faked the blur before.
 * Drift + the device-tilt parallax run as reanimated worklets on the UI thread.
 * Ported layout/keyframes from the design's mesh.jsx (meshA–D, the veil).
 */

interface BlobSpec {
  /** top/left/w as fractions of the oversized field (see FIELD_INSET) */
  top: number;
  left: number;
  w: number;
  /** ambient blobs are taller; cards stay circular (h omitted) */
  h?: number;
  dur: number;
  delay: number;
  // drift end-state from the meshA–D keyframes, as fractions of card size
  dx: number;
  dy: number;
  s0: number;
  s1: number;
}

// The field is drawn 28% larger than the view and inset -14% so drift +
// parallax never pull a blob's soft edge into frame.
const FIELD_INSET = 0.14;
const FIELD_SCALE = 1 + FIELD_INSET * 2;

// Cards: blobs sized off the field so they stay round on wide cards.
const BLOBS_CARD: BlobSpec[] = [
  { top: -0.3, left: -0.12, w: 0.62, dur: 17, delay: 0, dx: 0.22, dy: 0.16, s0: 1, s1: 1.25 },
  { top: -0.18, left: 0.52, w: 0.58, dur: 21, delay: 4, dx: -0.2, dy: 0.18, s0: 1.1, s1: 0.92 },
  { top: 0.38, left: -0.08, w: 0.6, dur: 25, delay: 9, dx: 0.18, dy: -0.16, s0: 0.95, s1: 1.2 },
  { top: 0.34, left: 0.56, w: 0.66, dur: 19, delay: 6, dx: -0.16, dy: -0.2, s0: 1.15, s1: 0.95 },
];

// Screens: the original overlapping full-bleed layout.
const BLOBS_AMBIENT: BlobSpec[] = [
  { top: -0.1, left: -0.08, w: 0.78, h: 0.82, dur: 17, delay: 0, dx: 0.22, dy: 0.16, s0: 1, s1: 1.25 },
  { top: 0.08, left: 0.38, w: 0.74, h: 0.78, dur: 21, delay: 4, dx: -0.2, dy: 0.18, s0: 1.1, s1: 0.92 },
  { top: 0.34, left: -0.12, w: 0.82, h: 0.8, dur: 25, delay: 9, dx: 0.18, dy: -0.16, s0: 0.95, s1: 1.2 },
  { top: 0.3, left: 0.4, w: 0.88, h: 0.86, dur: 19, delay: 6, dx: -0.16, dy: -0.2, s0: 1.15, s1: 0.95 },
];

// parallax travel (px) at full tilt — matches the old interpolate ranges
const TILT_X = 84;
const TILT_Y = 60;

const fade = (hex: string, alpha: string) => `${hex}${alpha}`;

interface ResolvedBlob {
  cx: number;
  cy: number;
  r: number;
  color: string;
  spec: BlobSpec;
}

/** One drifting, breathing blob — its own progress worklet on the UI thread. */
function Blob({ blob, drift, speed }: { blob: ResolvedBlob; drift: number; speed: number }) {
  const { cx, cy, r, color, spec } = blob;
  const p = useSharedValue(0);

  useEffect(() => {
    if (speed <= 0) {
      cancelAnimation(p);
      p.value = 0;
      return;
    }
    const duration = (spec.dur * 1000) / speed;
    // negative animation-delay feel: stagger the loop starts
    p.value = withDelay(
      spec.delay * 100,
      withRepeat(withTiming(1, { duration, easing: Easing.inOut(Easing.ease) }), -1, true)
    );
    return () => cancelAnimation(p);
  }, [p, spec, speed]);

  const center = useDerivedValue(() => {
    'worklet';
    // a plain point, not vec() — vec isn't a worklet and would throw on the UI thread
    return { x: cx + spec.dx * drift * p.value, y: cy + spec.dy * drift * p.value };
  }, [cx, cy, drift, spec]);

  const radius = useDerivedValue(() => {
    'worklet';
    return r * (spec.s0 + (spec.s1 - spec.s0) * p.value);
  }, [r, spec]);

  return (
    <Circle c={center} r={radius}>
      {/* soft falloff; the group Blur turns it into a real gaussian glow */}
      <RadialGradient
        c={center}
        r={radius}
        colors={[fade(color, 'e6'), fade(color, '73'), fade(color, '00')]}
        positions={[0, 0.45, 1]}
      />
    </Circle>
  );
}

interface Props {
  palette: TonePalette;
  tilt?: Tilt;
  /** rough card size in dp, scales drift distance */
  drift?: number;
  /** veil strength: cards want strong, ambient backgrounds want soft */
  veil?: 'card' | 'ambient' | 'none';
  /** motion speed multiplier; 0 = static */
  speed?: number;
  /** film-grain overlay */
  grain?: boolean;
  /** how many blobs to draw (2–4) */
  blobCount?: number;
  style?: object;
}

export function MeshGradient({
  palette,
  tilt,
  drift = 110,
  veil = 'card',
  speed = 1,
  grain = true,
  blobCount = 4,
  style,
}: Props) {
  const [size, setSize] = useState({ w: 0, h: 0 });
  const { w, h } = size;

  // whole-field parallax shift (all blobs move together); identity without tilt
  const tiltTransform = useDerivedValue(() => {
    'worklet';
    if (!tilt) return [{ translateX: 0 }, { translateY: 0 }];
    return [{ translateX: tilt.x.value * -TILT_X }, { translateY: tilt.y.value * -TILT_Y }];
  }, [tilt]);

  const count = Math.max(2, Math.min(4, blobCount));
  const specs = (veil === 'ambient' ? BLOBS_AMBIENT : BLOBS_CARD).slice(0, count);

  // map the fractional specs onto the oversized field, in canvas pixels
  const fieldX = -FIELD_INSET * w;
  const fieldY = -FIELD_INSET * h;
  const fieldW = FIELD_SCALE * w;
  const fieldH = FIELD_SCALE * h;
  const blobs: ResolvedBlob[] = specs.map((spec, i) => {
    const diameter = spec.w * fieldW;
    const r = diameter / 2;
    const left = fieldX + spec.left * fieldW;
    const top = fieldY + spec.top * fieldH;
    const heightPx = spec.h ? spec.h * fieldH : diameter;
    return {
      cx: left + r,
      cy: top + heightPx / 2,
      r,
      color: palette.blobs[i % palette.blobs.length],
      spec,
    };
  });

  const blurRadius = Math.max(10, Math.min(40, Math.min(w, h) * 0.05));

  return (
    <View
      style={[StyleSheet.absoluteFill, { backgroundColor: palette.base, overflow: 'hidden' }, style]}
      onLayout={(e) => {
        const { width, height } = e.nativeEvent.layout;
        if (width !== w || height !== h) setSize({ w: width, h: height });
      }}
    >
      {w > 0 && h > 0 && (
        <Canvas style={StyleSheet.absoluteFill}>
          <Group transform={tiltTransform}>
            <Group>
              {/* the real gaussian blur, applied to every blob in this group */}
              <Blur blur={blurRadius} />
              {blobs.map((blob, i) => (
                <Blob key={i} blob={blob} drift={drift} speed={speed} />
              ))}
            </Group>
          </Group>
          {veil !== 'none' && (
            <Rect x={0} y={0} width={w} height={h}>
              <LinearGradient
                start={vec(0, 0)}
                end={vec(0, h)}
                colors={
                  veil === 'card'
                    ? ['#0000000d', '#0000001a', '#0000006b']
                    : ['#07051066', '#070510eb', '#070510ff']
                }
                positions={veil === 'card' ? [0, 0.42, 1] : [0, 0.38, 1]}
              />
            </Rect>
          )}
        </Canvas>
      )}
      {grain && (
        <Image
          source={require('../../assets/mesh/noise.png')}
          resizeMode="repeat"
          style={[StyleSheet.absoluteFill, { width: undefined, height: undefined, opacity: 0.55 }]}
        />
      )}
    </View>
  );
}
