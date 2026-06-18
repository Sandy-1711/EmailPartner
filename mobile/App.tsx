import {
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
  useFonts,
} from '@expo-google-fonts/space-grotesk';
import * as Linking from 'expo-linking';
import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { usePushRegistration } from './src/hooks/usePushRegistration';
import { clearToken, getToken, setToken } from './src/lib/config';
import { FeedScreen } from './src/screens/FeedScreen';
import { SignInScreen } from './src/screens/SignInScreen';
import { colors } from './src/theme';
import { TweaksProvider } from './src/tweaks';

type AuthState = 'loading' | 'signedOut' | 'signedIn';

export default function App() {
  const [auth, setAuth] = useState<AuthState>('loading');
  const [playCardId, setPlayCardId] = useState<string | null>(null);
  const [readCardId, setReadCardId] = useState<string | null>(null);
  const url = Linking.useURL();
  const [fontsLoaded] = useFonts({
    SpaceGrotesk_400Regular,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
  });

  useEffect(() => {
    getToken().then((token) => setAuth(token ? 'signedIn' : 'signedOut'));
  }, []);

  usePushRegistration(auth === 'signedIn');

  // Handles both emailpartner://auth?token=... (sign-in fallback when the
  // browser fires the deep link directly) and emailpartner://play/<cardId>
  // (widget tap -> open app and narrate that card).
  useEffect(() => {
    if (!url) return;
    const { hostname, path, queryParams } = Linking.parse(url);
    if (hostname === 'auth' && typeof queryParams?.token === 'string') {
      setToken(queryParams.token).then(() => setAuth('signedIn'));
    } else if (hostname === 'play') {
      const cardId = (path ?? '').replace(/^\//, '');
      if (cardId) setPlayCardId(cardId);
    } else if (hostname === 'read') {
      const cardId = (path ?? '').replace(/^\//, '');
      if (cardId) setReadCardId(cardId);
    }
  }, [url]);

  const onToken = useCallback((token: string) => {
    setToken(token).then(() => setAuth('signedIn'));
  }, []);

  const onSignOut = useCallback(() => {
    clearToken().then(() => setAuth('signedOut'));
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
    <TweaksProvider>
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <StatusBar style="light" />
      {auth === 'loading' || !fontsLoaded ? (
        <View style={{ flex: 1, justifyContent: 'center' }}>
          <ActivityIndicator color={colors.accent} />
        </View>
      ) : auth === 'signedOut' ? (
        <SignInScreen onToken={onToken} />
      ) : (
        <FeedScreen
          onSignOut={onSignOut}
          playCardId={playCardId}
          onPlayedRequestedCard={() => setPlayCardId(null)}
          readCardId={readCardId}
          onReadHandled={() => setReadCardId(null)}
        />
      )}
    </View>
    </TweaksProvider>
    </GestureHandlerRootView>
  );
}
