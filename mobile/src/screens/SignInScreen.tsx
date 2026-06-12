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

import { MeshGradient } from '../components/MeshGradient';
import { getSignInUrl } from '../lib/api';
import { DEFAULT_SERVER, getServerUrl, setServerUrl } from '../lib/config';
import { colors, fonts } from '../theme';
import { TONES } from '../tones';

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
      <MeshGradient palette={TONES.urgent} veil="ambient" drift={200} />
      <View style={styles.content}>
        <Text style={styles.brand}>ECHO MAIL</Text>
        <Text style={styles.title}>Every email,{'\n'}one breath long.</Text>
        <Text style={styles.subtitle}>
          Your Gmail, distilled: a phrase you can read at a glance, a voice that reads the rest —
          on your home screen.
        </Text>

        <Text style={styles.label}>SERVER URL</Text>
        <TextInput
          style={styles.input}
          value={server}
          onChangeText={setServer}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          placeholder="https://your-ngrok-url"
          placeholderTextColor="rgba(255,255,255,0.35)"
        />

        <Pressable style={styles.button} onPress={signIn} disabled={busy}>
          {busy ? (
            <ActivityIndicator color="#0a0612" />
          ) : (
            <Text style={styles.buttonText}>Sign in with Google</Text>
          )}
        </Pressable>

        {error ? <Text style={styles.error}>{error}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { flex: 1, justifyContent: 'center', padding: 28 },
  brand: {
    color: 'rgba(255,255,255,0.6)',
    fontFamily: fonts.semibold,
    fontSize: 12,
    letterSpacing: 2,
    marginBottom: 14,
  },
  title: {
    color: '#fff',
    fontFamily: fonts.semibold,
    fontSize: 42,
    lineHeight: 44,
    letterSpacing: -1.2,
    marginBottom: 16,
  },
  subtitle: {
    color: 'rgba(255,255,255,0.62)',
    fontFamily: fonts.regular,
    fontSize: 15,
    lineHeight: 23,
    marginBottom: 40,
  },
  label: {
    color: 'rgba(255,255,255,0.5)',
    fontFamily: fonts.semibold,
    fontSize: 11,
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    borderRadius: 14,
    color: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 13,
    marginBottom: 18,
    fontFamily: fonts.medium,
    fontSize: 15,
  },
  button: {
    backgroundColor: '#f0d6ff',
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: 'center',
  },
  buttonText: { color: '#0a0612', fontFamily: fonts.bold, fontSize: 16 },
  error: {
    color: colors.danger,
    marginTop: 16,
    fontFamily: fonts.regular,
    fontSize: 13,
    lineHeight: 19,
  },
});
