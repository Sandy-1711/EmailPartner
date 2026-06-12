import { requireNativeModule } from 'expo-modules-core';

interface NarrationNative {
  play(id: string, url: string, title: string, artist: string): boolean;
  stop(): boolean;
  currentId(): string | null;
}

/**
 * Native singleton narration service (modules/narration): one foreground
 * MediaSessionService + ExoPlayer, used for widget-initiated playback so it
 * works without the app open and stop never depends on a JS player handle.
 * Wrapped so JS keeps working (no-op) if the native module isn't in the
 * installed binary yet.
 */
function native(): NarrationNative | null {
  try {
    return requireNativeModule<NarrationNative>('Narration');
  } catch {
    return null;
  }
}

export const Narration = {
  play(id: string, url: string, title: string, artist: string): boolean {
    return native()?.play(id, url, title, artist) ?? false;
  },
  stop(): boolean {
    return native()?.stop() ?? false;
  },
  currentId(): string | null {
    return native()?.currentId() ?? null;
  },
};
