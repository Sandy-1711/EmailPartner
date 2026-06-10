import { registerRootComponent } from 'expo';
import { registerWidgetTaskHandler } from 'react-native-android-widget';

import App from './App';
import { widgetTaskHandler } from './src/widget/widget-task-handler';

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// The widget task handler runs headless when Android asks the widget to render.
registerRootComponent(App);
registerWidgetTaskHandler(widgetTaskHandler);
