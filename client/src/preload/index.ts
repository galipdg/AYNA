import { contextBridge, ipcRenderer } from 'electron'
import { IPC, type AynaApi } from '../shared/api.ts'

const api: AynaApi = {
  getAppInfo: () => ipcRenderer.invoke(IPC.getAppInfo),
  getSettings: () => ipcRenderer.invoke(IPC.getSettings),
  checkServer: (url) => ipcRenderer.invoke(IPC.checkServer, url),
  connectServer: (url) => ipcRenderer.invoke(IPC.connectServer, url),
  listApplications: () => ipcRenderer.invoke(IPC.listApplications),
  createApplication: (name, technology) =>
    ipcRenderer.invoke(IPC.createApplication, name, technology),
  chooseApplication: (id) => ipcRenderer.invoke(IPC.chooseApplication, id),
}

// Only these functions cross the bridge; ipcRenderer itself never reaches the renderer.
contextBridge.exposeInMainWorld('ayna', Object.freeze(api))
