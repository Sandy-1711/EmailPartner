// gesture-handler must be the very first import in the entry file so its
// native module is initialized before any view mounts — the UI-thread scrub
// gesture silently no-ops otherwise.
import 'react-native-gesture-handler';

import { registerRootComponent } from 'expo';

import App from './App';

// The home-screen widget is now fully native (modules/echowidget) — no JS task
// handler. registerRootComponent calls AppRegistry.registerComponent('main', () => App).
registerRootComponent(App);
