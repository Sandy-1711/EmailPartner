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

let headlessPlayer: AudioPlayer | null = null;
let headlessPlayingId: string | null = null;

export function headlessPlayingCardId(): string | null {
  return headlessPlayingId;
}

function stopHeadless() {
  try {
    headlessPlayer?.clearLockScreenControls();
  } catch {}
  headlessPlayer?.remove();
  headlessPlayer = null;
  headlessPlayingId = null;
}

async function playHeadless(data: Record<string, unknown>): Promise<void> {
  const id = typeof data.id === 'string' ? data.id : null;
  const audioUrl = typeof data.audioUrl === 'string' ? data.audioUrl : null;
  if (!id || !audioUrl) return;

  if (headlessPlayingId === id) {
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
  headlessPlayer = player;
  headlessPlayingId = id;
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
        <CardWidget card={card} message={message} playingId={headlessPlayingId} />
      );
      break;
    }
    case 'WIDGET_CLICK': {
      if (props.clickAction === 'PLAY_NARRATION' && props.clickActionData) {
        await playHeadless(props.clickActionData);
        const { card, message } = await fetchWidgetCard();
        props.renderWidget(
          <CardWidget card={card} message={message} playingId={headlessPlayingId} />
        );
      }
      break;
    }
    default:
      break;
  }
}
