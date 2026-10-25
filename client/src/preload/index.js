import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/api.js'

/** @type {import('../shared/api.js').AynaApi} */
const api = {
  getAppInfo: () => ipcRenderer.invoke(IPC.getAppInfo),
}

// Only these functions cross the bridge; ipcRenderer itself never reaches the renderer.
contextBridge.exposeInMainWorld('ayna', Object.freeze(api))
