import { LinearGradient } from 'expo-linear-gradient';
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import Svg, { Defs, Ellipse, RadialGradient, Stop } from 'react-native-svg';

import type { Tilt } from '../hooks/useTilt';
import type { TonePalette } from '../tones';

/**
 * Echo Mail mesh gradient: several colored blobs drifting under a blur —
 * not a single linear ramp. Ported from the design's mesh.jsx:
 * blob layout, drift keyframes (meshA–D) and the readability veil.
 * RN can't blur, so each blob is a real SVG radial gradient (soft falloff),
 * which reads the same. `tilt` adds the device-motion parallax on top.
 */

interface BlobSpec {
  top: string;
  left: string;
  w: string;
  h: string;
  dur: number;
  delay: number;
  // drift end-state from the meshA–D keyframes, as fractions of card size
  dx: number;
  dy: number;
  s0: number;
  s1: number;
}

const BLOBS: BlobSpec[] = [
  { top: '-10%', left: '-8%', w: '78%', h: '82%', dur: 17, delay: 0, dx: 0.22, dy: 0.16, s0: 1, s1: 1.25 },
  { top: '8%', left: '38%', w: '74%', h: '78%', dur: 21, delay: 4, dx: -0.2, dy: 0.18, s0: 1.1, s1: 0.92 },
  { top: '34%', left: '-12%', w: '82%', h: '80%', dur: 25, delay: 9, dx: 0.18, dy: -0.16, s0: 0.95, s1: 1.2 },
  { top: '30%', left: '40%', w: '88%', h: '86%', dur: 19, delay: 6, dx: -0.16, dy: -0.2, s0: 1.15, s1: 0.95 },
];

function Blob({ color, spec, drift }: { color: string; spec: BlobSpec; drift: number }) {
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(progress, {
          toValue: 1,
          duration: spec.dur * 1000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(progress, {
          toValue: 0,
          duration: spec.dur * 1000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );
    // stagger starts like the negative animation-delays in the design
    const timer = setTimeout(() => loop.start(), spec.delay * 100);
    return () => {
      clearTimeout(timer);
      loop.stop();
    };
  }, [progress, spec]);

  const translateX = progress.interpolate({ inputRange: [0, 1], outputRange: [0, spec.dx * drift] });
  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [0, spec.dy * drift] });
  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [spec.s0, spec.s1] });

  return (
    <Animated.View
      style={{
        position: 'absolute',
        top: spec.top as `${number}%`,
        left: spec.left as `${number}%`,
        width: spec.w as `${number}%`,
        height: spec.h as `${number}%`,
        transform: [{ translateX }, { translateY }, { scale }],
      }}
    >
      <Svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
        <Defs>
          <RadialGradient id="g" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={color} stopOpacity={0.9} />
            <Stop offset="32%" stopColor={color} stopOpacity={0.8} />
            <Stop offset="70%" stopColor={color} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Ellipse cx="50" cy="50" rx="50" ry="50" fill="url(#g)" />
      </Svg>
    </Animated.View>
  );
}

interface Props {
  palette: TonePalette;
  tilt?: Tilt;
  /** rough card size in dp, scales drift distance */
  drift?: number;
  /** veil strength: cards want strong, ambient backgrounds want soft */
  veil?: 'card' | 'ambient' | 'none';
  style?: object;
}

export function MeshGradient({ palette, tilt, drift = 110, veil = 'card', style }: Props) {
  const parallax = tilt
    ? [
        {
          translateX: tilt.x.interpolate({ inputRange: [-0.5, 0.5], outputRange: [42, -42] }),
        },
        {
          translateY: tilt.y.interpolate({ inputRange: [-0.5, 0.5], outputRange: [30, -30] }),
        },
      ]
    : [];

  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: palette.base, overflow: 'hidden' }, style]}>
      <Animated.View style={[styles.field, { transform: parallax }]}>
        {BLOBS.map((spec, i) => (
          <Blob key={i} color={palette.blobs[i % palette.blobs.length]} spec={spec} drift={drift} />
        ))}
      </Animated.View>
      {veil !== 'none' && (
        <LinearGradient
          colors={
            veil === 'card'
              ? ['rgba(0,0,0,0.05)', 'rgba(0,0,0,0.10)', 'rgba(0,0,0,0.42)']
              : ['rgba(7,5,16,0.4)', 'rgba(7,5,16,0.92)', '#070510']
          }
          locations={veil === 'card' ? [0, 0.42, 1] : [0, 0.38, 1]}
          style={StyleSheet.absoluteFill}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  // oversized so parallax + drift never reveal an edge (the design's inset: -14%)
  field: { position: 'absolute', top: '-14%', left: '-14%', width: '128%', height: '128%' },
});
