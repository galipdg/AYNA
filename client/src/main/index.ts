import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import {
  app,
  BrowserWindow,
  globalShortcut,
  ipcMain,
  screen,
  session,
  type IpcMainInvokeEvent,
} from 'electron'
import {
  IPC,
  type AppInfo,
  type NewRepoObject,
  type RepoObjectChange,
  type Role,
} from '../shared/api.ts'
import { isLanguage, languageFor } from '../shared/language.ts'
import type { StepDocument } from '../shared/steps.ts'
import { AgentManager, resolveAgentCommand } from './agent.ts'
import {
  isAllowedNavigation,
  isAllowedRequest,
  isTrustedSender,
  secureWebPreferences,
} from './security.ts'
import { createApplication, listApplications } from './apps.ts'
import { login, logout, type Session } from './auth.ts'
import {
  addToRepository,
  createVersion,
  deleteRepoObject,
  getRepoObject,
  listRepoObjects,
  listVersions,
  updateRepoObject,
} from './repository.ts'
import { checkServer } from './server.ts'
import {
  createTest,
  deleteTest,
  getTest,
  listTests,
  renameTest,
  saveSteps,
  validateSteps,
} from './testCases.ts'
import {
  createToken,
  createUser,
  listTokens,
  listUsers,
  removeUser,
  revokeToken,
  updateUser,
} from './users.ts'
import { loadSettings, saveSettings, SETTINGS_FILE, withServer } from './settings.ts'
import { Highlighter } from './overlay.ts'
import { isBounds, listWindows, PickHotkey, pickHotkeyLabel, snapshot } from './spy.ts'

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
let mainWindow: BrowserWindow | undefined

// The agent reports and expects physical pixels; Electron's cursor point is in DIPs.
// `dipToScreenPoint` exists on Windows only; elsewhere there is no UI Automation backend.
const pickHotkey = new PickHotkey(globalShortcut, () => {
  const cursor = screen.getCursorScreenPoint()
  const point = process.platform === 'win32' ? screen.dipToScreenPoint(cursor) : cursor
  mainWindow?.webContents.send(IPC.pick, { x: point.x, y: point.y })
})

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

  handle(IPC.getAppInfo, (): AppInfo => ({
    name: app.getName(),
    version: app.getVersion(),
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
    platform: process.platform,
  }))
  handle(IPC.getSettings, () => loadSettings(settingsFile))
  handle(IPC.getLanguage, async () => {
    const { language } = await loadSettings(settingsFile)
    return language ?? languageFor(app.getPreferredSystemLanguages())
  })
  handle(IPC.setLanguage, async (_event, language: unknown) => {
    if (!isLanguage(language)) throw new Error(`not a UI language: ${String(language)}`)
    const settings = await loadSettings(settingsFile)
    await saveSettings(settingsFile, { ...settings, language })
  })
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
    const { serverUrl, token } = await server()
    return track(await listApplications(serverUrl, { token }))
  })
  handle(IPC.createApplication, async (_event, name: unknown, technology: unknown) => {
    const { serverUrl, token } = await server()
    return track(await createApplication(serverUrl, String(name), String(technology), { token }))
  })
  handle(IPC.chooseApplication, async (_event, id) => {
    const settings = await loadSettings(settingsFile)
    await saveSettings(settingsFile, { ...settings, applicationId: String(id) })
  })
  handle(IPC.listVersions, async (_event, appId: unknown) => {
    const { serverUrl, token } = await server()
    return track(await listVersions(serverUrl, String(appId), { token }))
  })
  handle(IPC.createVersion, async (_event, appId: unknown, version: unknown) => {
    const { serverUrl, token } = await server()
    return track(await createVersion(serverUrl, String(appId), String(version), { token }))
  })
  // The server validates the whole object; the main process only forwards it.
  handle(IPC.addToRepository, async (_event, object: unknown) => {
    const { serverUrl, token } = await server()
    return track(await addToRepository(serverUrl, object as NewRepoObject, { token }))
  })
  handle(IPC.listRepoObjects, async (_event, appId: unknown) => {
    const { serverUrl, token } = await server()
    return track(await listRepoObjects(serverUrl, String(appId), { token }))
  })
  handle(IPC.getRepoObject, async (_event, id: unknown) => {
    const { serverUrl, token } = await server()
    return track(await getRepoObject(serverUrl, String(id), { token }))
  })
  // As for adding, the server checks the change.
  handle(IPC.updateRepoObject, async (_event, id: unknown, change: unknown) => {
    const { serverUrl, token } = await server()
    return track(
      await updateRepoObject(serverUrl, String(id), change as RepoObjectChange, { token }),
    )
  })
  handle(IPC.deleteRepoObject, async (_event, id: unknown) => {
    const { serverUrl, token } = await server()
    return track(await deleteRepoObject(serverUrl, String(id), { token }))
  })
  handle(IPC.listTests, async (_event, appId: unknown) => {
    const { serverUrl, token } = await server()
    return track(await listTests(serverUrl, String(appId), { token }))
  })
  handle(IPC.createTest, async (_event, appId: unknown, name: unknown) => {
    const { serverUrl, token } = await server()
    return track(await createTest(serverUrl, String(appId), String(name), { token }))
  })
  handle(IPC.getTest, async (_event, id: unknown) => {
    const { serverUrl, token } = await server()
    return track(await getTest(serverUrl, String(id), { token }))
  })
  handle(IPC.renameTest, async (_event, id: unknown, name: unknown) => {
    const { serverUrl, token } = await server()
    return track(await renameTest(serverUrl, String(id), String(name), { token }))
  })
  handle(IPC.deleteTest, async (_event, id: unknown) => {
    const { serverUrl, token } = await server()
    return track(await deleteTest(serverUrl, String(id), { token }))
  })
  // The server checks the steps again against the same schema and the repository.
  handle(IPC.saveSteps, async (_event, id: unknown, document: unknown) => {
    const { serverUrl, token } = await server()
    return track(await saveSteps(serverUrl, String(id), document as StepDocument, { token }))
  })
  handle(IPC.validateSteps, (_event, document: unknown) => validateSteps(document))
  handle(IPC.getAgentStatus, () => agent.getStatus())
  handle(IPC.retryAgent, () => agent.retry())
  handle(IPC.listWindows, () => listWindows(agent))
  handle(IPC.snapshot, (_event, windowHandle, budgetMs) => snapshot(agent, windowHandle, budgetMs))
  // Anything that is not a valid rectangle (null included) removes the frame.
  handle(IPC.highlight, (_event, bounds) =>
    isBounds(bounds) ? highlighter.show(bounds) : highlighter.hide(),
  )
  handle(IPC.setPickHotkey, (_event, enabled) => ({
    active: pickHotkey.set(enabled === true),
    label: pickHotkeyLabel(process.platform),
  }))
  handle(IPC.login, async (_event, username: unknown, password: unknown) => {
    const { serverUrl } = await server()
    const answer = await login(serverUrl, String(username), String(password))
    if (!answer.ok) return answer
    session = { ...answer.session, serverUrl: serverUrl! }
    return { ok: true, user: answer.session.user }
  })
  handle(IPC.logout, async () => {
    const { serverUrl, token } = await server()
    session = null
    if (token) await logout(serverUrl, token)
  })
  handle(IPC.currentUser, async () => {
    const { token } = await server()
    return token ? session!.user : null
  })
  // User management: the server decides who is an admin; the client only passes the call on.
  handle(IPC.listUsers, async () => {
    const { serverUrl, token } = await server()
    return track(await listUsers(serverUrl, { token }))
  })
  handle(IPC.createUser, async (_event, username: unknown, password: unknown, role: unknown) => {
    const { serverUrl, token } = await server()
    const name = String(username)
    return track(
      await createUser(serverUrl, name, String(password), String(role) as Role, { token }),
    )
  })
  handle(IPC.updateUser, async (_event, id: unknown, change: unknown) => {
    const { serverUrl, token } = await server()
    const { role, password } = (change ?? {}) as { role?: Role; password?: string }
    const result = track(await updateUser(serverUrl, String(id), { role, password }, { token }))
    // An admin who made themselves a tester: the client's menus follow the new role.
    if (result.ok && session?.user.id === result.user.id) {
      session.user = { ...session.user, role: result.user.role }
    }
    return result
  })
  handle(IPC.removeUser, async (_event, id: unknown) => {
    const { serverUrl, token } = await server()
    return track(await removeUser(serverUrl, String(id), { token }))
  })
  handle(IPC.listTokens, async (_event, userId: unknown) => {
    const { serverUrl, token } = await server()
    return track(await listTokens(serverUrl, String(userId), { token }))
  })
  handle(IPC.createToken, async (_event, userId: unknown, name: unknown) => {
    const { serverUrl, token } = await server()
    return track(await createToken(serverUrl, String(userId), String(name), { token }))
  })
  handle(IPC.revokeToken, async (_event, tokenId: unknown) => {
    const { serverUrl, token } = await server()
    return track(await revokeToken(serverUrl, String(tokenId), { token }))
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
  window.on('closed', () => {
    highlighter.destroy()
    pickHotkey.set(false)
    if (mainWindow === window) mainWindow = undefined
  })
  // A reload unmounts the Spy without its cleanup; the new page turns the key on again.
  window.webContents.on('did-start-navigation', (details) => {
    if (details.isMainFrame && !details.isSameDocument) pickHotkey.set(false)
  })
  mainWindow = window
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
