import { DeviceMotion } from 'expo-sensors';
import { useEffect, useRef } from 'react';
import { Animated } from 'react-native';

export interface Tilt {
  x: Animated.Value;
  y: Animated.Value;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/**
 * One shared device-tilt signal for all cards: gamma (roll) drives x,
 * beta (pitch, re-centered around the natural ~40° holding angle) drives y.
 * Values are radians clamped to ±0.5, smoothed with short native-driver springs.
 */
export function useTilt(): Tilt {
  const tilt = useRef<Tilt>({
    x: new Animated.Value(0),
    y: new Animated.Value(0),
  }).current;

  useEffect(() => {
    DeviceMotion.setUpdateInterval(60);
    const subscription = DeviceMotion.addListener(({ rotation }) => {
      if (!rotation) return;
      Animated.parallel([
        Animated.spring(tilt.x, {
          toValue: clamp(rotation.gamma, -0.5, 0.5),
          useNativeDriver: true,
          speed: 20,
          bounciness: 0,
        }),
        Animated.spring(tilt.y, {
          toValue: clamp(rotation.beta - 0.7, -0.5, 0.5),
          useNativeDriver: true,
          speed: 20,
          bounciness: 0,
        }),
      ]).start();
    });
    return () => subscription.remove();
  }, [tilt]);

  return tilt;
}
