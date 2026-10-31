import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { app, BrowserWindow, ipcMain, session, type IpcMainInvokeEvent } from 'electron'
import { IPC, type AppInfo } from '../shared/api.ts'
import { AgentManager, resolveAgentCommand } from './agent.ts'
import {
  isAllowedNavigation,
  isAllowedRequest,
  isTrustedSender,
  secureWebPreferences,
} from './security.ts'
import { createApplication, listApplications } from './apps.ts'
import { checkServer } from './server.ts'
import { loadSettings, saveSettings, SETTINGS_FILE, withServer } from './settings.ts'
import { Highlighter } from './overlay.ts'
import { isBounds, listWindows } from './spy.ts'

// Set by `electron-vite dev`; absent in a built app.
const devServerUrl = app.isPackaged ? undefined : process.env.ELECTRON_RENDERER_URL
const entryUrl = devServerUrl ?? pathToFileURL(join(__dirname, '../renderer/index.html')).href

function hardenSession() {
  const ses = session.defaultSession
  // Closed network: cancel any request that is not the app itself, even if the CSP misses it.
  ses.webRequest.onBeforeRequest((details, callback) => {
    callback({ cancel: !isAllowedRequest(details.url, devServerUrl) })
  })
  ses.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false))
}

app.on('web-contents-created', (_event, contents) => {
  contents.on('will-navigate', (event, url) => {
    if (!isAllowedNavigation(url, entryUrl)) event.preventDefault()
  })
  contents.on('will-attach-webview', (event) => event.preventDefault())
  contents.setWindowOpenHandler(() => ({ action: 'deny' }))
})

const agent = new AgentManager({
  command: resolveAgentCommand({
    env: process.env,
    platform: process.platform,
    appPath: app.getAppPath(),
  }),
})
const highlighter = new Highlighter()

agent.onStatus((status) => {
  for (const window of BrowserWindow.getAllWindows()) {
    window.webContents.send(IPC.agentStatus, status)
  }
})

/** `ipcMain.handle` that refuses calls from any frame other than the app's own page. */
function handle(
  channel: string,
  listener: (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown,
) {
  ipcMain.handle(channel, (event, ...args) => {
    if (!isTrustedSender(event.senderFrame?.url, entryUrl)) {
      throw new Error(`IPC ${channel} refused: untrusted sender`)
    }
    return listener(event, ...args)
  })
}

function registerIpc() {
  const settingsFile = join(app.getPath('userData'), SETTINGS_FILE)

  handle(IPC.getAppInfo, (): AppInfo => ({
    name: app.getName(),
    version: app.getVersion(),
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
    platform: process.platform,
  }))
  handle(IPC.getSettings, () => loadSettings(settingsFile))
  // The check runs here, not in the renderer: the renderer's CSP allows no remote
  // connections, and Node's fetch is not subject to the session's request filter.
  handle(IPC.checkServer, (_event, url) => checkServer(String(url)))
  handle(IPC.connectServer, async (_event, url) => {
    const result = await checkServer(String(url))
    if (result.ok) {
      const settings = await loadSettings(settingsFile)
      await saveSettings(settingsFile, withServer(settings, result.url))
    }
    return result
  })
  handle(IPC.listApplications, async () => {
    const { serverUrl } = await loadSettings(settingsFile)
    return listApplications(serverUrl)
  })
  handle(IPC.createApplication, async (_event, name, technology) => {
    const { serverUrl } = await loadSettings(settingsFile)
    return createApplication(serverUrl, String(name), String(technology))
  })
  handle(IPC.chooseApplication, async (_event, id) => {
    const settings = await loadSettings(settingsFile)
    await saveSettings(settingsFile, { ...settings, applicationId: String(id) })
  })
  handle(IPC.getAgentStatus, () => agent.getStatus())
  handle(IPC.retryAgent, () => agent.retry())
  handle(IPC.listWindows, () => listWindows(agent))
  // Anything that is not a valid rectangle (null included) removes the frame.
  handle(IPC.highlight, (_event, bounds) =>
    isBounds(bounds) ? highlighter.show(bounds) : highlighter.hide(),
  )
}

function createMainWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: 'AYNA',
    show: false,
    webPreferences: secureWebPreferences(join(__dirname, '../preload/index.js')),
  })
  window.once('ready-to-show', () => window.show())
  window.on('closed', () => highlighter.destroy())
  window.loadURL(entryUrl)
}

app.whenReady().then(() => {
  hardenSession()
  registerIpc()
  createMainWindow()
  agent.start()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
  })
})

// Quit waits for the agent to stop, so no agent outlives the client.
let agentStopped = false
app.on('before-quit', (event) => {
  if (agentStopped) return
  event.preventDefault()
  agent.stop().finally(() => {
    agentStopped = true
    app.quit()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
