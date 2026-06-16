import type { ConfigContext, ExpoConfig } from 'expo/config';

// The home-screen widget is a native local module (modules/echowidget): it
// registers its own AppWidgetProvider via the module manifest, so no widget
// config plugin is needed here.

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'EmailPartner',
  slug: 'emailpartner',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'dark',
  backgroundColor: '#0b0d12',
  scheme: 'emailpartner',
  android: {
    package: 'com.emailpartner.app',
    adaptiveIcon: {
      backgroundColor: '#0b0d12',
      foregroundImage: './assets/android-icon-foreground.png',
      backgroundImage: './assets/android-icon-background.png',
      monochromeImage: './assets/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },
  plugins: [
    'expo-audio',
    'expo-web-browser',
    'expo-secure-store',
  ],
});
