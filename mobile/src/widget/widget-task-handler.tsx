import { AudioPlayer, createAudioPlayer, setAudioModeAsync } from 'expo-audio';
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

export function headlessPlayingCardId(): string | null {
  return registry().playingId;
}

function stopHeadless() {
  const reg = registry();
  try {
    reg.player?.clearLockScreenControls();
  } catch {}
  try {
    reg.player?.remove();
  } catch {}
  reg.player = null;
  reg.playingId = null;
}

async function playHeadless(data: Record<string, unknown>): Promise<void> {
  const id = typeof data.id === 'string' ? data.id : null;
  const audioUrl = typeof data.audioUrl === 'string' ? data.audioUrl : null;
  if (!id || !audioUrl) return;

  const reg = registry();
  if (reg.playingId === id) {
    // second tap on the same card = stop (also covers a lost player handle:
    // clear state so the next tap starts clean instead of stacking players)
    stopHeadless();
    return;
  }
  stopHeadless();

  await setAudioModeAsync({
    playsInSilentMode: true,
    shouldPlayInBackground: true,
    shouldRouteThroughEarpiece: false,
    interruptionMode: 'doNotMix',
  }).catch(() => {});

  const player = createAudioPlayer({ uri: audioUrl });
  player.addListener('playbackStatusUpdate', (status) => {
    if (status.didJustFinish) stopHeadless();
  });
  reg.player = player;
  reg.playingId = id;
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
      const { card, message } = await fetchWidgetCard();
      props.renderWidget(
        <CardWidget card={card} message={message} playingId={registry().playingId} />
      );
      break;
    }
    case 'WIDGET_CLICK': {
      if (props.clickAction === 'PLAY_NARRATION' && props.clickActionData) {
        await playHeadless(props.clickActionData);
        const { card, message } = await fetchWidgetCard();
        props.renderWidget(
          <CardWidget card={card} message={message} playingId={registry().playingId} />
        );
      }
      break;
    }
    default:
      break;
  }
}
