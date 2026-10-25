// Contract between the preload bridge and the renderer. The renderer only ever
// sees `window.ayna`, shaped like `AynaApi`; every method maps to one IPC channel.

/**
 * @typedef {object} AppInfo
 * @property {string} name
 * @property {string} version
 * @property {string} electron
 * @property {string} chrome
 * @property {string} node
 * @property {string} platform
 */

/**
 * @typedef {object} AynaApi
 * @property {() => Promise<AppInfo>} getAppInfo
 */

export const IPC = Object.freeze({
  getAppInfo: 'app:get-info',
})
