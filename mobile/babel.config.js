module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // Reanimated 4 moved worklet transforms into react-native-worklets; its
    // babel plugin must be LISTED LAST (it is the only plugin here). Without it,
    // every worklet (the Skia mesh drift + the UI-thread scrub gesture) throws
    // at runtime.
    plugins: ['react-native-worklets/plugin'],
  };
};
