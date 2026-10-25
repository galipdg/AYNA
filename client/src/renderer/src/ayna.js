// The only way the renderer reaches the main process: the bridge exposed by src/preload.

/** @type {import('../../shared/api.js').AynaApi} */
export const ayna = /** @type {any} */ (window).ayna
