import { requireNativeModule } from 'expo-modules-core';

export interface EchoWidgetCard {
  id: string;
  phrase: string;
  sender: string;
  tone: string | null;
  hasAudio: boolean;
  audioUrl: string | null;
}

interface EchoWidgetNative {
  setCards(json: string): void;
  refresh(): void;
}

/**
 * Native StackView home-screen widget (modules/echowidget): a swipeable deck of
 * the latest cards, drawn entirely natively (real-blur mesh, crisp text), playing
 * via NarrationService directly. The app owns the data and pushes it here.
 * Wrapped so JS no-ops if the native module isn't in the installed binary yet.
 */
function native(): EchoWidgetNative | null {
  try {
    return requireNativeModule<EchoWidgetNative>('EchoWidget');
  } catch {
    return null;
  }
}

export const EchoWidget = {
  /** Push the latest cards (the native side caps the deck). */
  setCards(cards: EchoWidgetCard[]): void {
    native()?.setCards(JSON.stringify(cards));
  },
  /** Re-render from current data (e.g. play-state changed). */
  refresh(): void {
    native()?.refresh();
  },
};
