import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'ep_session_token';
const SERVER_KEY = 'ep_server_url';

// 10.0.2.2 reaches the host machine from the Android emulator; on a real
// phone this gets replaced with an ngrok/LAN URL on the sign-in screen.
export const DEFAULT_SERVER = 'http://10.0.2.2:8000';

export async function getServerUrl(): Promise<string> {
  return (await SecureStore.getItemAsync(SERVER_KEY)) ?? DEFAULT_SERVER;
}

export async function setServerUrl(url: string): Promise<void> {
  await SecureStore.setItemAsync(SERVER_KEY, url.trim().replace(/\/+$/, ''));
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}
