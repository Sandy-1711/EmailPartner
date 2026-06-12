import { useCallback, useEffect, useRef, useState } from 'react';

import { EmailCard, phraseOf, senderOf } from '../lib/api';
import { Narration } from '../lib/narration';

export interface Playback {
  playingId: string | null;
  /** false while paused (in-app, lock screen, or notification) */
  isPlaying: boolean;
  /** 0..1 for the currently playing card */
  progress: number;
  /** seconds; 0 while unknown */
  duration: number;
  toggle: (card: EmailCard) => void;
  /** press-in warm-up; kept for API compatibility (native start is fast) */
  preload: (card: EmailCard) => void;
  /** scrub the active narration; fraction 0..1 */
  seekTo: (fraction: number) => void;
  stop: () => void;
}

/**
 * All playback runs in the native NarrationService (modules/narration):
 * one ExoPlayer + MediaSession in a foreground service, shared with the
 * widget. One player = one output route (no more earpiece+speaker mixes),
 * stop always works, and the lock screen gets controls for free. This hook
 * just sends commands and mirrors the service state for the waveforms.
 */
export function usePlayback(): Playback {
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  // After a user command, the optimistic UI state wins over polled status
  // briefly — the player reports "not playing" while buffering.
  const commandAtRef = useRef(0);
  const durationMsRef = useRef(0);

  // mirror the service state (covers widget-started playback, lock-screen
  // pause/resume, and track end) at 4Hz while the screen is open
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const status = await Narration.getStatus();
        durationMsRef.current = status.durationMs;
        if (Date.now() - commandAtRef.current > 900) {
          setPlayingId(status.id);
          setIsPlaying(status.playing);
        }
        if (status.id && status.durationMs > 0) {
          setDuration(status.durationMs / 1000);
          setProgress(Math.min(1, status.positionMs / status.durationMs));
        } else if (!status.id) {
          setProgress(0);
          setDuration(0);
        }
      } catch {
        // native module missing in this binary; nothing to mirror
      }
    }, 250);
    return () => clearInterval(interval);
  }, []);

  const stop = useCallback(() => {
    commandAtRef.current = Date.now();
    Narration.stop();
    setPlayingId(null);
    setIsPlaying(false);
    setProgress(0);
    setDuration(0);
  }, []);

  const toggle = useCallback(
    (card: EmailCard) => {
      if (!card.audio_url) return;
      commandAtRef.current = Date.now();
      if (playingId === card.id) {
        Narration.pausePlay();
        setIsPlaying((p) => !p);
        return;
      }
      Narration.play(card.id, card.audio_url, phraseOf(card), senderOf(card));
      setPlayingId(card.id);
      setIsPlaying(true);
      setProgress(0);
    },
    [playingId]
  );

  const preload = useCallback((_card: EmailCard) => {
    // ExoPlayer prepare-on-play is fast enough; kept as a no-op hook point.
  }, []);

  const seekTo = useCallback((fraction: number) => {
    if (durationMsRef.current <= 0) return;
    const clamped = Math.max(0, Math.min(1, fraction));
    commandAtRef.current = Date.now();
    setProgress(clamped);
    Narration.seekToMs(clamped * durationMsRef.current);
  }, []);

  useEffect(() => stop, [stop]);

  return { playingId, isPlaying, progress, duration, toggle, preload, seekTo, stop };
}
