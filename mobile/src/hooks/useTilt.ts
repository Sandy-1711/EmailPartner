import { Accelerometer } from 'expo-sensors';
import { useEffect } from 'react';
import { type SharedValue, useSharedValue, withSpring } from 'react-native-reanimated';

export interface Tilt {
  x: SharedValue<number>;
  y: SharedValue<number>;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

// short, critically-damped spring — smooths the 60ms accelerometer samples
// without bounce; runs entirely on the UI thread.
const SPRING = { mass: 0.4, damping: 16, stiffness: 130 } as const;

/**
 * One shared device-tilt signal for all cards, derived from the gravity
 * vector (accelerometer in g units — universally available on Android,
 * unlike DeviceMotion.rotation which is null on many devices).
 * x: left/right roll; y: pitch re-centered around the natural ~35° holding
 * angle. Clamped to ±0.5.
 *
 * Reanimated SharedValues (not RN Animated) so the Skia MeshGradient can read
 * the parallax in a worklet on the UI thread — Animated.Value can't be read
 * off the JS thread.
 */
export function useTilt(): Tilt {
  const x = useSharedValue(0);
  const y = useSharedValue(0);

  useEffect(() => {
    Accelerometer.setUpdateInterval(60);
    const subscription = Accelerometer.addListener(({ x: ax, y: ay }) => {
      x.value = withSpring(clamp(-ax, -0.5, 0.5), SPRING);
      y.value = withSpring(clamp(ay - 0.55, -0.5, 0.5), SPRING);
    });
    return () => subscription.remove();
  }, [x, y]);

  return { x, y };
}
