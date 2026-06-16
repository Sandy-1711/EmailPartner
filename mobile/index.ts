// gesture-handler must be the very first import in the entry file so its
// native module is initialized before any view mounts — the UI-thread scrub
// gesture silently no-ops otherwise.
import 'react-native-gesture-handler';

import { registerRootComponent } from 'expo';
import { registerWidgetTaskHandler } from 'react-native-android-widget';

import App from './App';
import { widgetTaskHandler } from './src/widget/widget-task-handler';

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// The widget task handler runs headless when Android asks the widget to render.
registerRootComponent(App);
registerWidgetTaskHandler(widgetTaskHandler);
