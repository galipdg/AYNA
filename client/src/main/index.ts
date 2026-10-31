import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { app, BrowserWindow, ipcMain, session } from 'electron'
import { IPC, type AppInfo } from '../shared/api.ts'
import { isAllowedNavigation, isAllowedRequest, secureWebPreferences } from './security.ts'
import { createApplication, listApplications } from './apps.ts'
import { login, logout, type Session } from './auth.ts'
import { checkServer } from './server.ts'
import { loadSettings, saveSettings, SETTINGS_FILE, withServer } from './settings.ts'

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

function registerIpc() {
  const settingsFile = join(app.getPath('userData'), SETTINGS_FILE)
  // In memory only: closing the client logs out. Tied to the server it came from.
  let session: (Session & { serverUrl: string }) | null = null

  /** The saved server and the session token for it, if any. */
  async function server() {
    const { serverUrl } = await loadSettings(settingsFile)
    const token = session && session.serverUrl === serverUrl ? session.token : null
    return { serverUrl, token }
  }

  /** A 401 means the session is gone on the server; forget it here too. */
  function track<T extends { ok: boolean; reason?: string }>(result: T): T {
    if (!result.ok && result.reason === 'unauthorized') session = null
    return result
  }

  ipcMain.handle(IPC.getAppInfo, (): AppInfo => ({
    name: app.getName(),
    version: app.getVersion(),
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
    platform: process.platform,
  }))
  ipcMain.handle(IPC.getSettings, () => loadSettings(settingsFile))
  // The check runs here, not in the renderer: the renderer's CSP allows no remote
  // connections, and Node's fetch is not subject to the session's request filter.
  ipcMain.handle(IPC.checkServer, (_event, url: unknown) => checkServer(String(url)))
  ipcMain.handle(IPC.connectServer, async (_event, url: unknown) => {
    const result = await checkServer(String(url))
    if (result.ok) {
      const settings = await loadSettings(settingsFile)
      await saveSettings(settingsFile, withServer(settings, result.url))
    }
    return result
  })
  ipcMain.handle(IPC.listApplications, async () => {
    const { serverUrl, token } = await server()
    return track(await listApplications(serverUrl, { token }))
  })
  ipcMain.handle(IPC.createApplication, async (_event, name: unknown, technology: unknown) => {
    const { serverUrl, token } = await server()
    return track(await createApplication(serverUrl, String(name), String(technology), { token }))
  })
  ipcMain.handle(IPC.chooseApplication, async (_event, id: unknown) => {
    const settings = await loadSettings(settingsFile)
    await saveSettings(settingsFile, { ...settings, applicationId: String(id) })
  })
  ipcMain.handle(IPC.login, async (_event, username: unknown, password: unknown) => {
    const { serverUrl } = await server()
    const answer = await login(serverUrl, String(username), String(password))
    if (!answer.ok) return answer
    session = { ...answer.session, serverUrl: serverUrl! }
    return { ok: true, user: answer.session.user }
  })
  ipcMain.handle(IPC.logout, async () => {
    const { serverUrl, token } = await server()
    session = null
    if (token) await logout(serverUrl, token)
  })
  ipcMain.handle(IPC.currentUser, async () => {
    const { token } = await server()
    return token ? session!.user : null
  })
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
  window.loadURL(entryUrl)
}

app.whenReady().then(() => {
  hardenSession()
  registerIpc()
  createMainWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
