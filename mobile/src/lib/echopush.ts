import { requireNativeModule } from 'expo-modules-core';
import type { EventSubscription } from 'expo-modules-core';

export interface PermissionResponse {
  status: 'granted' | 'denied' | 'undetermined';
  granted: boolean;
  canAskAgain: boolean;
}

interface EchoPushNative {
  getToken(): Promise<string>;
  requestPermission(): Promise<PermissionResponse>;
  getPermission(): Promise<PermissionResponse>;
  addListener(event: 'onTokenRefresh', cb: (e: { token: string }) => void): EventSubscription;
}

/**
 * FCM bridge (modules/echopush). The native EchoPushService receives pushes and
 * posts the per-email notification + widget refresh even when the app is closed;
 * here JS only fetches the device token (to register with the backend) and asks
 * for the POST_NOTIFICATIONS permission. No-ops if the module isn't in the
 * installed binary yet (older build) so the app keeps working.
 */
function native(): EchoPushNative | null {
  try {
    return requireNativeModule<EchoPushNative>('EchoPush');
  } catch {
    return null;
  }
}

export const EchoPush = {
  /** The device FCM token, or null if FCM isn't available in this binary. */
  async getToken(): Promise<string | null> {
    const n = native();
    if (!n) return null;
    try {
      return await n.getToken();
    } catch {
      return null;
    }
  },
  /** Ask for notification permission (Android 13+); granted by default below. */
  async requestPermission(): Promise<boolean> {
    const n = native();
    if (!n) return false;
    try {
      return (await n.requestPermission()).granted;
    } catch {
      return false;
    }
  },
  /** Subscribe to token rotation so we can re-register with the backend. */
  onTokenRefresh(cb: (token: string) => void): EventSubscription | null {
    return native()?.addListener('onTokenRefresh', (e) => cb(e.token)) ?? null;
  },
};
