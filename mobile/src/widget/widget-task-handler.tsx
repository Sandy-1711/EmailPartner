import {
  AudioPlayer,
  createAudioPlayer,
  setAudioModeAsync,
  setIsAudioActiveAsync,
} from 'expo-audio';
import * as SecureStore from 'expo-secure-store';
import React from 'react';
import type { WidgetTaskHandlerProps } from 'react-native-android-widget';

import { EmailCard, getCards, phraseOf, senderOf } from '../lib/api';
import { getToken } from '../lib/config';
import { CardWidget, WidgetCard } from './CardWidget';

export function toWidgetCard(card: EmailCard): WidgetCard {
  return {
    id: card.id,
    phrase: phraseOf(card),
    sender: senderOf(card),
    tone: card.tone,
    hasAudio: card.audio_url != null,
    audioUrl: card.audio_url,
  };
}

export function latestReadyCard(cards: EmailCard[]): WidgetCard | null {
  const ready = cards.find((card) => card.processing_status === 'ready');
  return ready ? toWidgetCard(ready) : null;
}

async function fetchWidgetCard(): Promise<{ card: WidgetCard | null; message?: string }> {
  const token = await getToken();
  if (!token) {
    return { card: null, message: 'Sign in to see your cards' };
  }
  try {
    const data = await getCards(10);
    const card = latestReadyCard(data.items);
    return card
      ? { card }
      : { card: null, message: 'No cards yet — send yourself an email' };
  } catch {
    return { card: null, message: 'Open the app to refresh' };
  }
}

/* ---------- headless playback (widget tap, app never opens) ---------- */

// Stored on globalThis: module state can be lost when Android tears the
// headless JS context down between widget clicks; globalThis survives as
// long as the process does (the MediaSession foreground service holds it).
interface HeadlessAudio {
  player: AudioPlayer | null;
  playingId: string | null;
}

function registry(): HeadlessAudio {
  const g = globalThis as typeof globalThis & { __epHeadlessAudio?: HeadlessAudio };
  if (!g.__epHeadlessAudio) {
    g.__epHeadlessAudio = { player: null, playingId: null };
  }
  return g.__epHeadlessAudio;
}

// The headless JS context can be destroyed between widget taps, losing the
// player handle. The playing-id therefore lives in SecureStore (survives
// anything), and stopping uses setIsAudioActiveAsync(false), which natively
// pauses every player in the process — no handle required.
const PLAYING_KEY = 'ep_widget_playing';

async function storedPlayingId(): Promise<string | null> {
  try {
    const raw = await SecureStore.getItemAsync(PLAYING_KEY);
    if (!raw) return null;
    const { id, at } = JSON.parse(raw) as { id: string; at: number };
    // stale after 5 minutes (didJustFinish may never fire if the context died)
    if (Date.now() - at > 5 * 60_000) return null;
    return id;
  } catch {
    return null;
  }
}

export function headlessPlayingCardId(): string | null {
  return registry().playingId;
}

async function stopHeadless() {
  const reg = registry();
  try {
    reg.player?.clearLockScreenControls();
  } catch {}
  try {
    reg.player?.remove();
  } catch {}
  reg.player = null;
  reg.playingId = null;
  await setIsAudioActiveAsync(false).catch(() => {}); // pauses orphans too
  await SecureStore.deleteItemAsync(PLAYING_KEY).catch(() => {});
}

async function playHeadless(data: Record<string, unknown>): Promise<void> {
  const id = typeof data.id === 'string' ? data.id : null;
  const audioUrl = typeof data.audioUrl === 'string' ? data.audioUrl : null;
  if (!id || !audioUrl) return;

  const reg = registry();
  const playing = reg.playingId ?? (await storedPlayingId());
  if (playing === id) {
    await stopHeadless();
    return;
  }
  await stopHeadless();
  await setIsAudioActiveAsync(true).catch(() => {});

  await setAudioModeAsync({
    playsInSilentMode: true,
    shouldPlayInBackground: true,
    shouldRouteThroughEarpiece: false,
    interruptionMode: 'doNotMix',
  }).catch(() => {});

  const player = createAudioPlayer({ uri: audioUrl });
  player.addListener('playbackStatusUpdate', (status) => {
    if (status.didJustFinish) void stopHeadless();
  });
  reg.player = player;
  reg.playingId = id;
  await SecureStore.setItemAsync(PLAYING_KEY, JSON.stringify({ id, at: Date.now() })).catch(
    () => {}
  );
  player.play();
  try {
    // The MediaSession foreground service keeps the headless process alive
    // for the duration of playback and puts controls on the lock screen.
    player.setActiveForLockScreen(
      true,
      {
        title: typeof data.phrase === 'string' ? data.phrase : 'Email summary',
        artist: typeof data.sender === 'string' ? data.sender : undefined,
        albumTitle: 'Echo Mail',
      },
      { showSeekForward: false, showSeekBackward: false }
    );
  } catch {}
}

export async function widgetTaskHandler(props: WidgetTaskHandlerProps) {
  switch (props.widgetAction) {
    case 'WIDGET_ADDED':
    case 'WIDGET_UPDATE':
    case 'WIDGET_RESIZED': {
      const [{ card, message }, playingId] = await Promise.all([
        fetchWidgetCard(),
        storedPlayingId(),
      ]);
      props.renderWidget(
        <CardWidget card={card} message={message} playingId={registry().playingId ?? playingId} />
      );
      break;
    }
    case 'WIDGET_CLICK': {
      if (props.clickAction === 'PLAY_NARRATION' && props.clickActionData) {
        await playHeadless(props.clickActionData);
        const [{ card, message }, playingId] = await Promise.all([
          fetchWidgetCard(),
          storedPlayingId(),
        ]);
        props.renderWidget(
          <CardWidget
            card={card}
            message={message}
            playingId={registry().playingId ?? playingId}
          />
        );
      }
      break;
    }
    default:
      break;
  }
}
