import { requireNativeModule } from 'expo-modules-core';

export interface NarrationStatus {
  id: string | null;
  playing: boolean;
  positionMs: number;
  durationMs: number;
}

interface NarrationNative {
  play(id: string, url: string, title: string, artist: string): boolean;
  stop(): boolean;
  pausePlay(): void;
  seekToMs(positionMs: number): void;
  currentId(): string | null;
  getStatus(): Promise<NarrationStatus>;
}

/**
 * Native singleton narration service (modules/narration): one foreground
 * MediaSessionService + ExoPlayer for ALL narration playback — app and
 * widget. One player means one output route (speaker), working stop, and
 * lock-screen controls everywhere. Wrapped so JS keeps working (no-op) if
 * the native module isn't in the installed binary yet.
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
  pausePlay(): void {
    native()?.pausePlay();
  },
  seekToMs(positionMs: number): void {
    native()?.seekToMs(positionMs);
  },
  currentId(): string | null {
    return native()?.currentId() ?? null;
  },
  async getStatus(): Promise<NarrationStatus> {
    const n = native();
    if (!n) return { id: null, playing: false, positionMs: 0, durationMs: 0 };
    return n.getStatus();
  },
};
