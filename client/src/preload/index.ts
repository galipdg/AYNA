import { contextBridge, ipcRenderer } from 'electron'
import { IPC, type AynaApi } from '../shared/api.ts'

const api: AynaApi = {
  getAppInfo: () => ipcRenderer.invoke(IPC.getAppInfo),
}

// Only these functions cross the bridge; ipcRenderer itself never reaches the renderer.
contextBridge.exposeInMainWorld('ayna', Object.freeze(api))
