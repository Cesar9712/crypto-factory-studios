export const GAME_CONFIG = Object.freeze({
  architectureVersion: 5,
  persistence: Object.freeze({ key: 'cryptoquest:architecture:v5', schemaVersion: 5, debounceMs: 120 }),
  screens: Object.freeze(['boot','home','adventure','hero','bag','talents','more','combat','bastion','dungeons','expeditions','shop']),
  mobileBreakpoints: Object.freeze([360,390,412]),
  compatibility: Object.freeze({ legacyRuntime: true }),
});
