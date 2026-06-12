import {
  AudioPlayer,
  createAudioPlayer,
  setAudioModeAsync,
  setIsAudioActiveAsync,
} from 'expo-audio';
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
  /** call on press-in so the stream is buffering before the tap lands */
  preload: (card: EmailCard) => void;
  /** scrub the active card; fraction 0..1 */
  seekTo: (fraction: number) => void;
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
  const preloadRef = useRef<{ id: string; player: AudioPlayer } | null>(null);
  // After a user command, ignore the ticker's playing-state sync briefly —
  // the player reports "not playing" while buffering, which flickered the icon.
  const commandAtRef = useRef(0);

  const preload = useCallback((card: EmailCard) => {
    if (!card.audio_url) return;
    if (preloadRef.current?.id === card.id || playerRef.current) return;
    try {
      preloadRef.current = { id: card.id, player: createAudioPlayer({ uri: card.audio_url }) };
    } catch {
      preloadRef.current = null;
    }
  }, []);

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
      setIsAudioActiveAsync(true).catch(() => {}); // widget stop may have disabled audio

      // use the preloaded (already buffering) player when available
      let player: AudioPlayer;
      if (preloadRef.current?.id === card.id) {
        player = preloadRef.current.player;
        preloadRef.current = null;
      } else {
        preloadRef.current?.player.remove();
        preloadRef.current = null;
        player = createAudioPlayer({ uri: card.audio_url });
      }
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

  const seekTo = useCallback((fraction: number) => {
    const p = playerRef.current;
    if (!p || p.duration <= 0) return;
    const clamped = Math.max(0, Math.min(1, fraction));
    commandAtRef.current = Date.now();
    setProgress(clamped);
    p.seekTo(clamped * p.duration);
  }, []);

  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
      shouldRouteThroughEarpiece: false, // narration belongs on the speaker
      interruptionMode: 'doNotMix', // required for lock-screen controls
    }).catch(() => {});
    return stop;
  }, [stop]);

  return { playingId, isPlaying, progress, duration, toggle, preload, seekTo, stop };
}
