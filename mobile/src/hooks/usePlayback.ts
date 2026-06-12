import { AudioPlayer, createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { useCallback, useEffect, useRef, useState } from 'react';

import type { EmailCard } from '../lib/api';

export interface Playback {
  playingId: string | null;
  /** 0..1 for the currently playing card */
  progress: number;
  /** seconds; 0 while unknown */
  duration: number;
  toggle: (card: EmailCard) => void;
  stop: () => void;
}

/** One audio player for the whole app; waveforms read progress from here. */
export function usePlayback(): Playback {
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const playerRef = useRef<AudioPlayer | null>(null);
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (tickerRef.current) clearInterval(tickerRef.current);
    tickerRef.current = null;
    playerRef.current?.remove();
    playerRef.current = null;
    setPlayingId(null);
    setProgress(0);
    setDuration(0);
  }, []);

  const toggle = useCallback(
    (card: EmailCard) => {
      if (!card.audio_url) return;
      if (playingId === card.id) {
        stop();
        return;
      }
      if (tickerRef.current) clearInterval(tickerRef.current);
      playerRef.current?.remove();

      const player = createAudioPlayer({ uri: card.audio_url });
      player.addListener('playbackStatusUpdate', (status) => {
        if (status.didJustFinish) stop();
      });
      playerRef.current = player;
      setPlayingId(card.id);
      setProgress(0);
      player.play();
      tickerRef.current = setInterval(() => {
        const p = playerRef.current;
        if (!p) return;
        if (p.duration > 0) {
          setDuration(p.duration);
          setProgress(Math.min(1, p.currentTime / p.duration));
        }
      }, 250);
    },
    [playingId, stop]
  );

  useEffect(() => {
    setAudioModeAsync({ playsInSilentMode: true }).catch(() => {});
    return stop;
  }, [stop]);

  return { playingId, progress, duration, toggle, stop };
}
