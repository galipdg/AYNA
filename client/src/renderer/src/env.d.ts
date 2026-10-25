/// <reference types="vite/client" />

import type { AynaApi } from '../../shared/api.ts'

declare global {
  interface Window {
    /** The only way to reach the main process: the bridge exposed by src/preload. */
    readonly ayna: AynaApi
  }
}
