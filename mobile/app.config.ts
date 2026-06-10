import type { ConfigContext, ExpoConfig } from 'expo/config';
import type { WithAndroidWidgetsParams } from 'react-native-android-widget';

const widgetConfig: WithAndroidWidgetsParams = {
  widgets: [
    {
      name: 'EmailCard',
      label: 'EmailPartner',
      description: 'Your latest email as art, with narration',
      minWidth: '250dp',
      minHeight: '110dp',
      targetCellWidth: 4,
      targetCellHeight: 2,
      resizeMode: 'horizontal|vertical',
      // Android enforces a 30 minute minimum; the app also refreshes the
      // widget whenever it fetches fresh cards.
      updatePeriodMillis: 1_800_000,
    },
  ],
};

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
    ['react-native-android-widget', widgetConfig],
  ],
});
