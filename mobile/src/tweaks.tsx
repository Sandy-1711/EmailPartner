import * as SecureStore from 'expo-secure-store';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { paletteFor, TonePalette } from './tones';

/**
 * User tweaks (from the design's Tweaks panel): gradient hue, motion speed,
 * font size, card density. Persisted on-device.
 */

export type Motion = 'off' | 'calm' | 'normal' | 'lively';
export type Density = 'compact' | 'cozy';

export interface Tweaks {
  motion: Motion;
  /** degrees of hue rotation applied to every tone palette */
  hue: number;
  fontScale: number;
  density: Density;
  grain: boolean;
  blobs: number;
}

export const DEFAULT_TWEAKS: Tweaks = {
  motion: 'normal',
  hue: 0,
  fontScale: 1,
  density: 'cozy',
  grain: true,
  blobs: 4,
};

export const MOTION_SPEED: Record<Motion, number> = {
  off: 0,
  calm: 0.55,
  normal: 1,
  lively: 1.7,
};

export const HUE_OPTIONS: { label: string; value: number }[] = [
  { label: 'Indigo', value: 0 },
  { label: 'Magenta', value: 40 },
  { label: 'Ocean', value: -60 },
  { label: 'Forest', value: 160 },
];

export const FONT_OPTIONS: { label: string; value: number }[] = [
  { label: 'S', value: 0.9 },
  { label: 'M', value: 1 },
  { label: 'L', value: 1.12 },
];

const STORE_KEY = 'ep_tweaks';

/* ---------- hue rotation ---------- */

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rotateHex(hex: `#${string}`, deg: number): `#${string}` {
  if (!deg) return hex;
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  if (d !== 0) {
    if (max === r) h = 60 * (((g - b) / d) % 6);
    else if (max === g) h = 60 * ((b - r) / d + 2);
    else h = 60 * ((r - g) / d + 4);
  }
  h = (h + deg + 360) % 360;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let rgb: [number, number, number];
  if (h < 60) rgb = [c, x, 0];
  else if (h < 120) rgb = [x, c, 0];
  else if (h < 180) rgb = [0, c, x];
  else if (h < 240) rgb = [0, x, c];
  else if (h < 300) rgb = [x, 0, c];
  else rgb = [c, 0, x];
  const out = rgb
    .map((v) => Math.round((v + m) * 255).toString(16).padStart(2, '0'))
    .join('');
  return `#${out}`;
}

export function rotatePalette(palette: TonePalette, deg: number): TonePalette {
  if (!deg) return palette;
  return {
    ...palette,
    base: rotateHex(palette.base, deg),
    blobs: palette.blobs.map((b) => rotateHex(b, deg)) as TonePalette['blobs'],
    accent: rotateHex(palette.accent, deg),
    dot: rotateHex(palette.dot, deg),
  };
}

/* ---------- context ---------- */

interface TweaksContextValue {
  tweaks: Tweaks;
  setTweak: <K extends keyof Tweaks>(key: K, value: Tweaks[K]) => void;
  /** tone palette with the user's hue rotation applied */
  palette: (tone: string | null | undefined) => TonePalette;
  speed: number;
}

const TweaksContext = createContext<TweaksContextValue>({
  tweaks: DEFAULT_TWEAKS,
  setTweak: () => {},
  palette: paletteFor,
  speed: 1,
});

export function TweaksProvider({ children }: { children: React.ReactNode }) {
  const [tweaks, setTweaks] = useState<Tweaks>(DEFAULT_TWEAKS);

  useEffect(() => {
    SecureStore.getItemAsync(STORE_KEY)
      .then((raw) => {
        if (raw) setTweaks({ ...DEFAULT_TWEAKS, ...JSON.parse(raw) });
      })
      .catch(() => {});
  }, []);

  const value = useMemo<TweaksContextValue>(() => {
    const cache = new Map<string, TonePalette>();
    return {
      tweaks,
      setTweak: (key, v) => {
        setTweaks((prev) => {
          const next = { ...prev, [key]: v };
          SecureStore.setItemAsync(STORE_KEY, JSON.stringify(next)).catch(() => {});
          return next;
        });
      },
      palette: (tone) => {
        const k = String(tone);
        let p = cache.get(k);
        if (!p) {
          p = rotatePalette(paletteFor(tone), tweaks.hue);
          cache.set(k, p);
        }
        return p;
      },
      speed: MOTION_SPEED[tweaks.motion],
    };
  }, [tweaks]);

  return <TweaksContext.Provider value={value}>{children}</TweaksContext.Provider>;
}

export function useTweaks(): TweaksContextValue {
  return useContext(TweaksContext);
}
