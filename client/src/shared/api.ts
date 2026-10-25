// Contract between the preload bridge and the renderer. The renderer only ever
// sees `window.ayna`, shaped like `AynaApi`; every method maps to one IPC channel.

export interface AppInfo {
  name: string
  version: string
  electron: string
  chrome: string
  node: string
  platform: string
}

export interface AynaApi {
  getAppInfo(): Promise<AppInfo>
}

export const IPC = {
  getAppInfo: 'app:get-info',
} as const
