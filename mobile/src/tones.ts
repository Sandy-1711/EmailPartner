/**
 * Echo Mail tone system (from the Claude Design handoff).
 * All palettes live in an indigo / violet / blue family — "urgent" pushes hot
 * toward magenta, "social" cools toward teal/cyan. Never orange.
 * Shared by the in-app screens and the home-screen widget.
 */
type Hex = `#${string}`;

export interface TonePalette {
  label: string;
  /** near-black tinted base behind the mesh */
  base: Hex;
  /** mesh blob colors, drawn as blurred radial gradients */
  blobs: [Hex, Hex, Hex, Hex];
  /** light accent for play buttons, filled waveform bars */
  accent: Hex;
  /** glowing tone indicator dot */
  dot: Hex;
}

export const TONES: Record<string, TonePalette> = {
  urgent: {
    label: 'Needs a reply',
    base: '#0c0510',
    blobs: ['#7c3aed', '#c026d3', '#5b21b6', '#4338ca'],
    accent: '#f0d6ff',
    dot: '#e879f9',
  },
  social: {
    label: 'Social',
    base: '#041018',
    blobs: ['#2563eb', '#06b6d4', '#0ea5e9', '#1d4ed8'],
    accent: '#cffafe',
    dot: '#38e1d6',
  },
  informative: {
    label: 'For your info',
    base: '#080b18',
    blobs: ['#4f5bd5', '#6366f1', '#3730a3', '#4f46e5'],
    accent: '#dde3ff',
    dot: '#8c95ff',
  },
  transactional: {
    label: 'Receipts & updates',
    base: '#070914',
    blobs: ['#6366f1', '#818cf8', '#4338ca', '#5b6ee0'],
    accent: '#e3e8ff',
    dot: '#a5b0ff',
  },
  promotional: {
    label: 'Promotion',
    base: '#0a0716',
    blobs: ['#8b5cf6', '#a855f7', '#4c1d95', '#6d28d9'],
    accent: '#ecdcff',
    dot: '#c084fc',
  },
};

export const DEFAULT_TONE = TONES.informative;

export function paletteFor(tone: string | null | undefined): TonePalette {
  return (tone && TONES[tone]) || DEFAULT_TONE;
}
