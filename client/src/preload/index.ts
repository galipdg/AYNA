import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import { IPC, type AgentStatus, type AynaApi, type ScreenPoint } from '../shared/api.ts'

const api: AynaApi = {
  getAppInfo: () => ipcRenderer.invoke(IPC.getAppInfo),
  getSettings: () => ipcRenderer.invoke(IPC.getSettings),
  checkServer: (url) => ipcRenderer.invoke(IPC.checkServer, url),
  connectServer: (url) => ipcRenderer.invoke(IPC.connectServer, url),
  listApplications: () => ipcRenderer.invoke(IPC.listApplications),
  createApplication: (name, technology) =>
    ipcRenderer.invoke(IPC.createApplication, name, technology),
  chooseApplication: (id) => ipcRenderer.invoke(IPC.chooseApplication, id),
  getAgentStatus: () => ipcRenderer.invoke(IPC.getAgentStatus),
  onAgentStatus: (listener) => {
    const forward = (_event: IpcRendererEvent, status: AgentStatus) => listener(status)
    ipcRenderer.on(IPC.agentStatus, forward)
    return () => ipcRenderer.removeListener(IPC.agentStatus, forward)
  },
  retryAgent: () => ipcRenderer.invoke(IPC.retryAgent),
  listWindows: () => ipcRenderer.invoke(IPC.listWindows),
  highlight: (bounds) => ipcRenderer.invoke(IPC.highlight, bounds),
  setPickHotkey: (enabled) => ipcRenderer.invoke(IPC.setPickHotkey, enabled),
  onPick: (listener) => {
    const forward = (_event: IpcRendererEvent, point: ScreenPoint) => listener(point)
    ipcRenderer.on(IPC.pick, forward)
    return () => ipcRenderer.removeListener(IPC.pick, forward)
  },
}

// Only these functions cross the bridge; ipcRenderer itself never reaches the renderer.
contextBridge.exposeInMainWorld('ayna', Object.freeze(api))
