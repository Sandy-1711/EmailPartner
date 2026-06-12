import { AudioPlayer, createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { useCallback, useEffect, useRef, useState } from 'react';

import { EmailCard, phraseOf, senderOf } from '../lib/api';

export interface Playback {
  playingId: string | null;
  /** false while paused from the lock screen / notification */
  isPlaying: boolean;
  /** 0..1 for the currently playing card */
  progress: number;
  /** seconds; 0 while unknown */
  duration: number;
  toggle: (card: EmailCard) => void;
  stop: () => void;
}

/**
 * One audio player for the whole app. Narration shows up on the lock screen
 * as a media session (like YouTube): phrase as title, sender as artist —
 * play/pause from the notification controls the same player.
 */
export function usePlayback(): Playback {
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const playerRef = useRef<AudioPlayer | null>(null);
  const tickerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // After a user command, ignore the ticker's playing-state sync briefly —
  // the player reports "not playing" while buffering, which flickered the icon.
  const commandAtRef = useRef(0);

  const stop = useCallback(() => {
    if (tickerRef.current) clearInterval(tickerRef.current);
    tickerRef.current = null;
    try {
      playerRef.current?.clearLockScreenControls();
    } catch {}
    playerRef.current?.remove();
    playerRef.current = null;
    setPlayingId(null);
    setIsPlaying(false);
    setProgress(0);
    setDuration(0);
  }, []);

  const toggle = useCallback(
    (card: EmailCard) => {
      if (!card.audio_url) return;
      if (playingId === card.id) {
        // tapping the active card: pause/resume rather than restart
        const p = playerRef.current;
        if (p) {
          commandAtRef.current = Date.now();
          if (p.playing) {
            p.pause();
            setIsPlaying(false);
          } else {
            p.play();
            setIsPlaying(true);
          }
          return;
        }
        stop();
        return;
      }
      if (tickerRef.current) clearInterval(tickerRef.current);
      try {
        playerRef.current?.clearLockScreenControls();
      } catch {}
      playerRef.current?.remove();

      const player = createAudioPlayer({ uri: card.audio_url });
      player.addListener('playbackStatusUpdate', (status) => {
        if (status.didJustFinish) stop();
      });
      playerRef.current = player;
      commandAtRef.current = Date.now();
      setPlayingId(card.id);
      setIsPlaying(true);
      setProgress(0);
      player.play();
      try {
        player.setActiveForLockScreen(
          true,
          { title: phraseOf(card), artist: senderOf(card), albumTitle: 'Echo Mail' },
          { showSeekForward: false, showSeekBackward: false }
        );
      } catch {}
      tickerRef.current = setInterval(() => {
        const p = playerRef.current;
        if (!p) return;
        if (Date.now() - commandAtRef.current > 900) {
          setIsPlaying(p.playing); // syncs lock-screen pause/resume only
        }
        if (p.duration > 0) {
          setDuration(p.duration);
          setProgress(Math.min(1, p.currentTime / p.duration));
        }
      }, 250);
    },
    [playingId, stop]
  );

  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
      shouldRouteThroughEarpiece: false, // narration belongs on the speaker
      interruptionMode: 'doNotMix', // required for lock-screen controls
    }).catch(() => {});
    return stop;
  }, [stop]);

  return { playingId, isPlaying, progress, duration, toggle, stop };
}
