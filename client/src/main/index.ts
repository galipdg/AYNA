import { randomUUID } from 'node:crypto'
import { rmSync } from 'node:fs'
import { mkdir, readFile, rm, unlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import {
  app,
  BrowserWindow,
  dialog,
  globalShortcut,
  ipcMain,
  screen,
  session,
  type IpcMainInvokeEvent,
} from 'electron'
import {
  IPC,
  RUN_STATUSES,
  type AppInfo,
  type NewRepoObject,
  type PickEvent,
  type RepoObjectChange,
  type ReportResult,
  type RunFilter,
  type RunStatus,
  type Role,
} from '../shared/api.ts'
import { isLanguage, languageFor } from '../shared/language.ts'
import type { StepDocument } from '../shared/steps.ts'
import { AgentManager, resolveAgentCommand } from './agent.ts'
import {
  isAllowedNavigation,
  isAllowedRequest,
  isTrustedSender,
  reportWebPreferences,
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
import {
  createRun,
  fetchReport,
  finishRun,
  getRun,
  listRunningRuns,
  listRuns,
  putResult,
  putScreenshot,
  reportFileName,
} from './runs.ts'
import type { LiveRun } from '../shared/liveRun.ts'
import { Outbox } from './outbox.ts'
import { Runner } from './runner.ts'
import { OWN_SCREENSHOT_DIR, removeOwnRunDir, screenshotKeeper } from './screenshots.ts'
import { RunEvents, type WebSocketLike } from './runEvents.ts'
import { perStepPlayer } from './stepPlayer.ts'
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
import {
  elementFromPoint,
  isBounds,
  listWindows,
  nativeHandle,
  AgentQueue,
  PickHotkey,
  pickHotkeyLabel,
  snapshot,
} from './spy.ts'

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
const agentQueue = new AgentQueue()
let mainWindow: BrowserWindow | undefined

const pickHotkey = new PickHotkey(globalShortcut, () => void pick())

/**
 * Asks the agent what is under the cursor and tells the Spy. The agent reports and expects
 * physical pixels; Electron's cursor point is in DIPs. `dipToScreenPoint` exists on Windows
 * only; elsewhere there is no UI Automation backend.
 */
async function pick() {
  const target = mainWindow
  if (!target) return
  const cursor = screen.getCursorScreenPoint()
  const { x, y } = process.platform === 'win32' ? screen.dipToScreenPoint(cursor) : cursor
  // The agent answers with what is visible at the point; the frame must not be that.
  const restoreFrame = highlighter.suspend()
  const result = await elementFromPoint(agent, { x, y }, agentQueue)
  if (target.isDestroyed()) return
  // A pick that selects a node frames it; any other answer leaves the frame that was showing.
  restoreFrame()
  const event: PickEvent = result.ok
    ? { point: { x, y }, ...result, ownWindow: isOwnWindow(result.hit.handle) }
    : { point: { x, y }, ...result }
  target.webContents.send(IPC.pick, event)
}

/** Whether `handle` is one of AYNA's windows: the main one, a report, the highlight frame. */
function isOwnWindow(handle: number | null): boolean {
  if (handle === null) return false
  return BrowserWindow.getAllWindows().some(
    (window) => nativeHandle(window.getNativeWindowHandle()) === handle,
  )
}

agent.onStatus((status) => {
  for (const window of BrowserWindow.getAllWindows()) {
    window.webContents.send(IPC.agentStatus, status)
  }
})

/** A run's changes go to every window: this client's run and the followed test's runs. */
function sendRun(run: LiveRun) {
  for (const window of BrowserWindow.getAllWindows()) window.webContents.send(IPC.run, run)
}

/** The run outbox's file in the user's data folder (#44). */
export const OUTBOX_FILE = 'run-outbox.json'

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
  /** The UI language: the user's choice, else the first-run rule. */
  async function uiLanguage() {
    const { language } = await loadSettings(settingsFile)
    return language ?? languageFor(app.getPreferredSystemLanguages())
  }

  handle(IPC.getLanguage, uiLanguage)
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
      // The session belongs to the previous server; so do its live runs.
      runEvents.setServer(null, null)
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
  handle(IPC.listRuns, async (_event, appId: unknown, filter: unknown) => {
    const { serverUrl, token } = await server()
    return track(await listRuns(serverUrl, String(appId), runFilter(filter), { token }))
  })
  handle(IPC.openReport, async (_event, runId: unknown): Promise<ReportResult> => {
    const { serverUrl, token } = await server()
    const report = track(await fetchReport(serverUrl, String(runId), await uiLanguage(), { token }))
    if (!report.ok) return report
    try {
      await showReport(String(runId), report.html)
    } catch (error) {
      return { ok: false, reason: 'write-failed', detail: String(error) }
    }
    return { ok: true }
  })
  handle(
    IPC.saveReport,
    async (event, runId: unknown, fileName: unknown): Promise<ReportResult> => {
      const owner = BrowserWindow.fromWebContents(event.sender)
      const options = {
        defaultPath: join(app.getPath('downloads'), reportFileName(String(fileName))),
        filters: [{ name: 'HTML', extensions: ['html'] }],
      }
      const choice = owner
        ? await dialog.showSaveDialog(owner, options)
        : await dialog.showSaveDialog(options)
      if (choice.canceled || !choice.filePath) return { ok: false, reason: 'cancelled' }
      const { serverUrl, token } = await server()
      const report = track(
        await fetchReport(serverUrl, String(runId), await uiLanguage(), { token }),
      )
      if (!report.ok) return report
      try {
        await writeFile(choice.filePath, report.html, 'utf8')
      } catch (error) {
        return { ok: false, reason: 'write-failed', detail: String(error) }
      }
      return { ok: true, path: choice.filePath }
    },
  )
  handle(IPC.getAgentStatus, () => agent.getStatus())
  handle(IPC.retryAgent, () => agent.retry())
  handle(IPC.listWindows, () => listWindows(agent))
  handle(IPC.snapshot, (_event, windowHandle, budgetMs) =>
    snapshot(agent, windowHandle, budgetMs, agentQueue),
  )
  // Anything that is not a valid rectangle (null included) removes the frame.
  handle(IPC.highlight, (_event, bounds) =>
    isBounds(bounds) ? highlighter.show(bounds) : highlighter.hide(),
  )
  handle(IPC.setPickHotkey, (_event, enabled) => ({
    active: pickHotkey.set(enabled === true),
    label: pickHotkeyLabel(process.platform),
  }))
  // Running a test from the editor (#44): results go through the outbox, which sends each to
  // the server it belongs to while a session for that server exists.
  // Step screenshots wait here until the outbox has sent them (#261).
  const screenshotRoot = join(app.getPath('userData'), OWN_SCREENSHOT_DIR)
  const screenshots = screenshotKeeper(screenshotRoot)
  const outboxReady = Outbox.open(join(app.getPath('userData'), OUTBOX_FILE), {
    serverUrl: () => session?.serverUrl ?? null,
    put: async (entry) => {
      const token = session && session.serverUrl === entry.serverUrl ? session.token : null
      if (!token) return 'unauthorized'
      let answer
      if (entry.kind === 'result') {
        answer = await putResult(entry.serverUrl, entry.runId, entry.body, { token })
      } else if (entry.kind === 'screenshot') {
        const png = await readFile(entry.path).catch(() => null)
        // An image gone from disk can never be sent; the outbox drops just that image.
        if (!png) return 'conflict'
        answer = await putScreenshot(entry.serverUrl, entry.runId, entry.stepIndex, png, { token })
      } else {
        answer = await finishRun(entry.serverUrl, entry.runId, entry.status, { token })
      }
      if (answer === 'unauthorized') session = null
      return answer
    },
    // Screenshots of the application under test: none stays on disk once it is no use.
    released: async (entry) => {
      if (entry.kind === 'screenshot') await unlink(entry.path).catch(() => undefined)
      if (entry.kind === 'finish') await removeOwnRunDir(screenshotRoot, entry.runId)
    },
  })
  const runEvents = new RunEvents({
    connect: (url, token) => {
      // Node's WebSocket (undici) takes handshake headers in its init object, as for the agent.
      const init = { headers: { Authorization: `Bearer ${token}` } } as unknown as string[]
      return new WebSocket(url, init) as unknown as WebSocketLike
    },
    catchUp: {
      running: async (testId) => {
        const { serverUrl, token } = await server()
        return track(await listRunningRuns(serverUrl, testId, { token }))
      },
      get: async (runId) => {
        const { serverUrl, token } = await server()
        return track(await getRun(serverUrl, runId, { token }))
      },
    },
  })
  runEvents.onRun((run) => {
    // This client's own run is told by the runner, which also knows the step being played.
    if (run.runId !== runner?.current()?.runId) sendRun(run)
  })
  let runner: Runner | null = null
  void outboxReady.then((outbox) => outbox.onSetAside((runId) => runner?.markNotStored(runId)))

  /** After a sign-in: deliver what waits, close runs a crash left open, follow live runs. */
  async function signedIn() {
    const { serverUrl, token } = await server()
    const outbox = await outboxReady
    if (serverUrl) {
      const playing = runner?.current()?.status === 'running' ? runner.current()!.runId : null
      for (const runId of outbox.unfinishedRuns(serverUrl)) {
        if (runId !== playing) {
          await outbox.add({ kind: 'finish', serverUrl, runId, status: 'aborted' })
        }
      }
    }
    outbox.resume()
    runEvents.setServer(serverUrl, token)
  }

  handle(IPC.startRun, async (_event, testId: unknown, appVersionId: unknown) => {
    const { serverUrl, token } = await server()
    if (runner?.current()?.status === 'running') return { ok: false, reason: 'busy' }
    const { applicationId } = await loadSettings(settingsFile)
    const outbox = await outboxReady
    const next = new Runner({
      createRun: async (test, version) =>
        track(await createRun(serverUrl, test, version, { token })),
      repoObjects: async () => {
        if (!applicationId) return null
        const answer = track(await listRepoObjects(serverUrl, applicationId, { token }))
        return answer.ok ? answer.objects : null
      },
      capturedElement: async (objectId) => {
        const answer = track(await getRepoObject(serverUrl, objectId, { token }))
        return answer.ok ? answer.object.element : undefined
      },
      agentConnected: () => agent.getStatus().state === 'connected',
      agent,
      player: perStepPlayer(agent),
      outbox,
      screenshots,
      serverUrl: serverUrl ?? '',
    })
    next.onChange(sendRun)
    const answer = await next.start(String(testId), String(appVersionId))
    if (answer.ok) runner = next
    return answer
  })
  handle(IPC.stopRun, () => runner?.stop())
  handle(IPC.chooseRunWindow, (_event, handle: unknown) =>
    runner?.choose(typeof handle === 'number' ? handle : null),
  )
  handle(IPC.watchRuns, (_event, testId: unknown) => {
    const id = typeof testId === 'string' ? testId : null
    runEvents.watch(id)
    const mine = runner?.current() ?? null
    return mine && mine.testId === id ? mine : null
  })
  handle(IPC.login, async (_event, username: unknown, password: unknown) => {
    const { serverUrl } = await server()
    const answer = await login(serverUrl, String(username), String(password))
    if (!answer.ok) return answer
    session = { ...answer.session, serverUrl: serverUrl! }
    await signedIn()
    return { ok: true, user: answer.session.user }
  })
  handle(IPC.logout, async () => {
    const { serverUrl, token } = await server()
    session = null
    runEvents.setServer(null, null)
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

/** Run report windows by run id; a run's report opens again in the same window (#68). */
const reportWindows = new Map<string, { window: BrowserWindow; file: string }>()
const reportFolder = () => join(app.getPath('temp'), 'ayna-reports')

/**
 * Shows a report in its own window, from a file in a private temp folder: a 15 MB page is too
 * large for a `data:` URL. The file goes when the window closes, and the folder when AYNA quits.
 */
async function showReport(runId: string, html: string) {
  await mkdir(reportFolder(), { recursive: true })
  const file = join(reportFolder(), `${randomUUID()}.html`)
  await writeFile(file, html, 'utf8')
  const open = reportWindows.get(runId)
  if (open && !open.window.isDestroyed()) {
    const previous = open.file
    open.file = file
    await open.window.loadFile(file)
    // Best effort: on Windows the file being replaced can still be locked (EBUSY), and the
    // report did open; the sweep at quit or the next start takes what is left (#231 review).
    void rm(previous, { force: true }).catch(() => {})
    open.window.focus()
    return
  }
  const window = new BrowserWindow({
    width: 1100,
    height: 850,
    minWidth: 480,
    minHeight: 400,
    show: false,
    autoHideMenuBar: true,
    webPreferences: reportWebPreferences(),
  })
  reportWindows.set(runId, { window, file })
  window.once('ready-to-show', () => window.show())
  window.on('closed', () => {
    const entry = reportWindows.get(runId)
    reportWindows.delete(runId)
    if (entry) void rm(entry.file, { force: true }).catch(() => {})
  })
  await window.loadFile(file)
}

/** The filter the renderer sent, keeping only what the server accepts. */
function runFilter(value: unknown): RunFilter {
  const filter: RunFilter = {}
  if (typeof value !== 'object' || value === null) return filter
  const { testId, status } = value as Record<string, unknown>
  if (typeof testId === 'string' && testId) filter.testId = testId
  if (RUN_STATUSES.includes(status as RunStatus)) filter.status = status as RunStatus
  return filter
}

/**
 * Removes every report file. They hold screenshots of the application under test, so none may
 * outlive AYNA: synchronous at quit (`will-quit` does not wait for a promise), and once at start
 * for what a crash or a kill left behind (#231 review).
 */
function sweepReports() {
  try {
    rmSync(reportFolder(), { recursive: true, force: true })
  } catch {
    // A file still locked by a closing window; the next start removes it.
  }
}

// A second instance that quits at once must not sweep the first one's open reports.
app.on('will-quit', () => {
  if (primaryInstance) sweepReports()
})

// One client per user-data folder: two would share `run-outbox.json`, and each rewrites the
// whole file (#44). Another folder (`--user-data-dir`) is another client.
const primaryInstance = app.requestSingleInstanceLock()
if (!primaryInstance) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow?.isMinimized()) mainWindow.restore()
    mainWindow?.focus()
  })
}

app.whenReady().then(() => {
  if (!primaryInstance) return
  sweepReports()
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
  if (agentStopped || !primaryInstance) return
  event.preventDefault()
  agent.stop().finally(() => {
    agentStopped = true
    app.quit()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
