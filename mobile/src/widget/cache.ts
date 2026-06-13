import * as SecureStore from 'expo-secure-store';

import type { WidgetCard } from './CardWidget';

const KEY = 'ep_widget_snapshot';

export interface WidgetSnapshot {
  card: WidgetCard | null;
  message?: string;
}

/**
 * The last data the widget rendered, persisted across widget events.
 *
 * The headless JS task context dies between events, so a module global can't
 * carry state — SecureStore does, and reads in single-digit ms (local, no
 * network). That lets a WIDGET_UPDATE re-render the play/stop icon INSTANTLY
 * from cache (the native service broadcasts one the moment playback ends),
 * instead of blocking the render on an HTTP fetch the way it used to.
 */
export async function readSnapshot(): Promise<WidgetSnapshot | null> {
  const raw = await SecureStore.getItemAsync(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as WidgetSnapshot;
  } catch {
    return null;
  }
}

export async function writeSnapshot(snap: WidgetSnapshot): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, JSON.stringify(snap));
  } catch {
    // best-effort cache; a failed write just means the next update fetches
  }
}

export function sameSnapshot(a: WidgetSnapshot | null, b: WidgetSnapshot): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
