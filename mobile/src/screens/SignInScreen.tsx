import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { getSignInUrl } from '../lib/api';
import { DEFAULT_SERVER, getServerUrl, setServerUrl } from '../lib/config';
import { colors, radius } from '../theme';

interface Props {
  onToken: (token: string) => void;
}

export function SignInScreen({ onToken }: Props) {
  const [server, setServer] = useState(DEFAULT_SERVER);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getServerUrl().then(setServer);
  }, []);

  async function signIn() {
    setBusy(true);
    setError(null);
    try {
      await setServerUrl(server);
      const authUrl = await getSignInUrl();
      const result = await WebBrowser.openAuthSessionAsync(authUrl, 'emailpartner://auth');
      if (result.type === 'success') {
        // Linking.parse instead of new URL(): Hermes' URL support is partial.
        const token = Linking.parse(result.url).queryParams?.token;
        if (typeof token === 'string' && token) {
          onToken(token);
          return;
        }
      }
      if (result.type !== 'cancel' && result.type !== 'dismiss') {
        setError('Sign-in did not complete. Try again.');
      }
    } catch (e) {
      setError(`Could not reach ${server}. Is the backend running and reachable from this phone?`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Every email,{'\n'}a tiny work of art.</Text>
      <Text style={styles.subtitle}>
        EmailPartner watches your Gmail and turns each new message into an illustrated,
        narrated card — right on your home screen.
      </Text>

      <Text style={styles.label}>Server URL</Text>
      <TextInput
        style={styles.input}
        value={server}
        onChangeText={setServer}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        placeholder="https://your-ngrok-url"
        placeholderTextColor={colors.textDim}
      />

      <Pressable style={styles.button} onPress={signIn} disabled={busy}>
        {busy ? (
          <ActivityIndicator color="#1b1f27" />
        ) : (
          <Text style={styles.buttonText}>Sign in with Google</Text>
        )}
      </Pressable>

      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 28, backgroundColor: colors.bg },
  title: { color: colors.text, fontSize: 38, fontWeight: '800', lineHeight: 44, marginBottom: 16 },
  subtitle: { color: colors.textDim, fontSize: 15, lineHeight: 22, marginBottom: 36 },
  label: { color: colors.textDim, fontSize: 12, marginBottom: 6, letterSpacing: 0.4 },
  input: {
    backgroundColor: colors.panel,
    borderColor: colors.panelBorder,
    borderWidth: 1,
    borderRadius: 12,
    color: colors.text,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 18,
    fontSize: 15,
  },
  button: {
    backgroundColor: '#fff',
    borderRadius: radius,
    paddingVertical: 15,
    alignItems: 'center',
  },
  buttonText: { color: '#1b1f27', fontWeight: '700', fontSize: 16 },
  error: { color: colors.danger, marginTop: 16, fontSize: 13, lineHeight: 19 },
});
