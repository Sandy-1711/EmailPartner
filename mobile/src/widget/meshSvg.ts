import type { TonePalette } from '../tones';

/**
 * The Echo Mail mesh, as an inline SVG string for the home-screen widget.
 *
 * Why a string and not the pre-rendered PNGs: SvgWidget renders this through
 * AndroidSVG (renderToPicture) entirely on the native side, so it does NOT go
 * through Metro asset resolution. `require()`d PNGs failed to load in the
 * widget's headless bitmap pass whenever Metro wasn't serving (debug builds) —
 * the texture vanished and only the flat gradient base showed. A string can't
 * fail that way: it renders identically in debug and release.
 *
 * Visually it mirrors the in-app MeshGradient: four soft radial blobs in the
 * tone palette over the same readability veil. Static (widgets don't animate).
 */

const W = 320;
const H = 150;

// Blob layout roughly matching MeshGradient's BLOBS_CARD spread, mapped to the
// 320x150 canvas. `c` indexes palette.blobs.
const BLOBS: { cx: number; cy: number; r: number; c: 0 | 1 | 2 | 3 }[] = [
  { cx: 54, cy: 28, r: 120, c: 0 },
  { cx: 270, cy: 40, r: 116, c: 1 },
  { cx: 68, cy: 150, r: 124, c: 2 },
  { cx: 292, cy: 150, r: 132, c: 3 },
];

// Same gaussian-like falloff as the in-app blobs — reads as glow, not a circle.
const STOPS: [number, number][] = [
  [0, 0.72],
  [0.22, 0.6],
  [0.42, 0.38],
  [0.62, 0.18],
  [0.82, 0.05],
  [1, 0],
];

export function meshSvg(palette: TonePalette): string {
  const grads = BLOBS.map((b, i) => {
    const color = palette.blobs[b.c];
    const stops = STOPS.map(
      ([off, op]) =>
        `<stop offset="${off * 100}%" stop-color="${color}" stop-opacity="${op}"/>`
    ).join('');
    return `<radialGradient id="g${i}" gradientUnits="userSpaceOnUse" cx="${b.cx}" cy="${b.cy}" r="${b.r}">${stops}</radialGradient>`;
  }).join('');

  const circles = BLOBS.map(
    (b, i) => `<circle cx="${b.cx}" cy="${b.cy}" r="${b.r}" fill="url(#g${i})"/>`
  ).join('');

  // Readability veil: transparent at the top, darkening toward the bottom where
  // the sender + phrase sit (matches MeshGradient's 'card' veil).
  const veil =
    `<linearGradient id="veil" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="${H}">` +
    `<stop offset="0%" stop-color="#000000" stop-opacity="0.05"/>` +
    `<stop offset="42%" stop-color="#000000" stop-opacity="0.10"/>` +
    `<stop offset="100%" stop-color="#000000" stop-opacity="0.42"/>` +
    `</linearGradient>`;

  // No solid base rect: the corners stay transparent so the gradient base
  // FlexWidget below shows through, and the clip rounds the bleed to match.
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
    `<defs>${grads}${veil}` +
    `<clipPath id="r"><rect x="0" y="0" width="${W}" height="${H}" rx="24" ry="24"/></clipPath></defs>` +
    `<g clip-path="url(#r)">${circles}<rect x="0" y="0" width="${W}" height="${H}" fill="url(#veil)"/></g>` +
    `</svg>`
  );
}
