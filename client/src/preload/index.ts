import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import { IPC, type AgentStatus, type AynaApi } from '../shared/api.ts'

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
}

// Only these functions cross the bridge; ipcRenderer itself never reaches the renderer.
contextBridge.exposeInMainWorld('ayna', Object.freeze(api))
