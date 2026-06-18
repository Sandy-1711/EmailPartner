import { useEffect } from 'react';

import { registerDevice } from '../lib/api';
import { EchoPush } from '../lib/echopush';

/**
 * Once signed in, ask for notification permission, fetch the FCM device token,
 * and register it with the backend so the worker can push freshly-narrated
 * emails. Re-registers if the token rotates. All native calls no-op on binaries
 * without the echopush module, so this is safe on older installs.
 */
export function usePushRegistration(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const register = async () => {
      await EchoPush.requestPermission();
      const token = await EchoPush.getToken();
      if (!token || cancelled) return;
      try {
        await registerDevice(token);
      } catch {
        // best-effort; a later app open or token refresh retries
      }
    };

    register();
    const sub = EchoPush.onTokenRefresh((token) => {
      registerDevice(token).catch(() => {});
    });

    return () => {
      cancelled = true;
      sub?.remove();
    };
  }, [enabled]);
}
