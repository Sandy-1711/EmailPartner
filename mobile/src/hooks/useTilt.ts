import { Accelerometer } from 'expo-sensors';
import { useEffect, useRef } from 'react';
import { Animated } from 'react-native';

export interface Tilt {
  x: Animated.Value;
  y: Animated.Value;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/**
 * One shared device-tilt signal for all cards, derived from the gravity
 * vector (accelerometer in g units — universally available on Android,
 * unlike DeviceMotion.rotation which is null on many devices).
 * x: left/right roll; y: pitch re-centered around the natural ~35° holding
 * angle. Clamped to ±0.5 and smoothed with short native-driver springs.
 */
export function useTilt(): Tilt {
  const tilt = useRef<Tilt>({
    x: new Animated.Value(0),
    y: new Animated.Value(0),
  }).current;

  useEffect(() => {
    Accelerometer.setUpdateInterval(60);
    const subscription = Accelerometer.addListener(({ x, y }) => {
      Animated.parallel([
        Animated.spring(tilt.x, {
          toValue: clamp(-x, -0.5, 0.5),
          useNativeDriver: true,
          speed: 20,
          bounciness: 0,
        }),
        Animated.spring(tilt.y, {
          toValue: clamp(y - 0.55, -0.5, 0.5),
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
