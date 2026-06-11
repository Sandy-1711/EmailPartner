/** Tone-driven palettes shared by the in-app cards and the home-screen widget. */
type Hex = `#${string}`;

export interface TonePalette {
  /** bright corner of the gradient */
  from: Hex;
  /** dark corner of the gradient */
  to: Hex;
  /** soft glow / accent elements */
  glow: Hex;
  /** dim supporting text */
  dim: Hex;
}

export const TONES: Record<string, TonePalette> = {
  urgent: { from: '#ff5a1f', to: '#160a05', glow: '#ff8a4d', dim: '#d8b39f' },
  informative: { from: '#3b6ce0', to: '#070b16', glow: '#6f96f5', dim: '#a9b6d6' },
  social: { from: '#f25c8a', to: '#170710', glow: '#ff8fb3', dim: '#d9aabb' },
  promotional: { from: '#9d4df0', to: '#10071c', glow: '#c08bff', dim: '#c3aede' },
  transactional: { from: '#1fb877', to: '#06130d', glow: '#5ad9a4', dim: '#a3c9b8' },
};

export const DEFAULT_TONE = TONES.informative;

export function paletteFor(tone: string | null | undefined): TonePalette {
  return (tone && TONES[tone]) || DEFAULT_TONE;
}
