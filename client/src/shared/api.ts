// Contract between the preload bridge and the renderer. The renderer only ever
// sees `window.ayna`, shaped like `AynaApi`; every method maps to one IPC channel.

import type { ElementDescriptor } from './element.ts'
import type { Language } from './language.ts'
import type { PropertySet } from './repository.ts'
import type { Snapshot } from './snapshot.ts'
import type { StepDocument, StepProblem } from './steps.ts'

export interface AppInfo {
  name: string
  version: string
  electron: string
  chrome: string
  node: string
  platform: string
}

/** Per-machine settings, stored by the main process in the user data folder. */
export interface Settings {
  /** Normalised server base URL (e.g. `http://ayna-server:8080`), or null before first run. */
  serverUrl: string | null
  /** The chosen application on that server; cleared when the server changes (ids are per server). */
  applicationId: string | null
  /** The UI language the user chose; null until they choose (then the system's is used). */
  language: Language | null
}

/** An application under test, as the server's `/api/apps` returns it. */
export interface Application {
  id: string
  name: string
  technology: string
}

/** A version of an application under test (`/api/apps/{appId}/versions`). */
export interface AppVersion {
  id: string
  version: string
}

export type Role = 'admin' | 'tester'

/** The signed-in account, as the server's `/api/auth/login` returns it (#60). */
export interface CurrentUser {
  id: string
  username: string
  role: Role
}

/** An account in the admin's user list (`/api/users`). */
export interface Account extends CurrentUser {
  createdAt: string
}

/** A CI API token of an account; the server never shows its secret again. */
export interface ApiToken {
  id: string
  name: string
  createdAt: string
}

/** Why a request to the saved server failed. */
export type RequestFailure =
  | 'no-server' // no server saved yet
  | 'unreachable'
  | 'timeout'
  | 'unauthorized' // no session, or it expired or was ended: log in again
  | 'bad-response' // the server answered with something unexpected

/** The session token stays in the main process; the renderer only learns who is signed in. */
export type LoginResult =
  { ok: true; user: CurrentUser } | { ok: false; reason: RequestFailure | 'wrong-credentials' }

export type ApplicationsResult =
  { ok: true; apps: Application[] } | { ok: false; reason: RequestFailure }

export type CreateApplicationResult =
  { ok: true; app: Application } | { ok: false; reason: RequestFailure | 'duplicate' | 'invalid' }

export type VersionsResult =
  { ok: true; versions: AppVersion[] } | { ok: false; reason: RequestFailure }

export type CreateVersionResult =
  | { ok: true; version: AppVersion }
  | { ok: false; reason: RequestFailure | 'duplicate' | 'invalid' | 'not-found'; detail?: string }

/** A picked element to store in the application's object repository (#25). */
export interface NewRepoObject {
  appId: string
  /** The version the capture belongs to; the snapshot is imported under it first. */
  versionId: string
  snapshot: Snapshot
  /** The picked element's id inside `snapshot`. */
  snapshotElementId: string
  /** Logical name, `screen.element`. */
  name: string
  primary: PropertySet
  fallback: PropertySet
}

/** A stored repository object, as the server returns it. */
export interface RepoObject {
  id: string
  name: string
  primary: PropertySet
  fallback: PropertySet
}

/** One row of the repository list (#30). */
export interface RepoObjectSummary extends RepoObject {
  /** From the most recent capture of the element; for search and display. */
  controlType?: string
  nearestLabel?: string
  /** How many tests have a step on this object (FR-08). */
  testCount: number
  /** The application versions the object is found in. */
  versionIds: string[]
}

/** A test that uses a repository object. */
export interface TestRef {
  id: string
  name: string
}

/** One repository object with everything the details panel shows (#30). */
export interface RepoObjectDetails extends RepoObject {
  versionIds: string[]
  usedBy: TestRef[]
  /** The element as last captured, in the descriptor's order; the editor starts from it. */
  element: Partial<ElementDescriptor>
}

/** A rename, new property sets (both together), or both. */
export interface RepoObjectChange {
  name?: string
  primary?: PropertySet
  fallback?: PropertySet
}

/** One field the server refused, e.g. `$.name` (problem details `errors`). */
export interface FieldProblem {
  path: string
  message: string
}

export type AddToRepositoryResult =
  | { ok: true; object: RepoObject }
  | {
      ok: false
      reason:
        | RequestFailure
        | 'duplicate' // the logical name is taken in this application
        | 'invalid' // `fields` says which
        | 'not-found' // the application or version is gone
        | 'snapshot-conflict' // this capture is already stored under another version
      detail?: string
      fields?: FieldProblem[]
    }

export interface RepoObjectError {
  ok: false
  reason:
    | RequestFailure
    | 'not-found' // the object (or application) is gone
    | 'invalid' // `fields` says which
    | 'duplicate' // the new name is taken in this application
    | 'in-use' // tests still use the object; `detail` names them
  detail?: string
  fields?: FieldProblem[]
}

export type RepoObjectsResult = { ok: true; objects: RepoObjectSummary[] } | RepoObjectError
export type RepoObjectResult = { ok: true; object: RepoObjectDetails } | RepoObjectError
export type RepoDeleteResult = { ok: true } | RepoObjectError

/** One row of the test list (#39). */
export interface TestSummary {
  id: string
  name: string
  stepCount: number
}

/** A test with its steps; the steps carry the ids the server gave them. */
export interface TestCase {
  id: string
  name: string
  document: StepDocument
  /** Who changed the test last, and when (ISO time). */
  updatedBy?: string
  updatedAt: string
}

export interface TestError {
  ok: false
  reason:
    | RequestFailure
    | 'not-found' // the test (or application) is gone
    | 'invalid' // `fields` says which, e.g. `$.steps[2].target`
    | 'duplicate' // the name is taken in this application
  detail?: string
  fields?: FieldProblem[]
}

export type TestsResult = { ok: true; tests: TestSummary[] } | TestError
export type TestResult = { ok: true; test: TestCase } | TestError
export type TestDeleteResult = { ok: true } | TestError

/** Why a user-management request failed; `detail` is the server's own message, when it sent one. */
export interface UsersError {
  ok: false
  reason:
    | RequestFailure
    | 'forbidden' // the signed-in account is not an admin
    | 'not-found' // the account or token is gone (removed by another admin)
    | 'invalid' // e.g. a user name or password the server does not accept
    | 'conflict' // e.g. the name is taken, or the last admin would be lost
  detail?: string
}

export type UsersResult = { ok: true; users: Account[] } | UsersError
export type UserResult = { ok: true; user: Account } | UsersError
export type TokensResult = { ok: true; tokens: ApiToken[] } | UsersError
/** `secret` is shown to the admin this once; the server keeps only its hash. */
export type CreatedTokenResult = { ok: true; token: ApiToken; secret: string } | UsersError
export type DoneResult = { ok: true } | UsersError

/** Why a server URL could not be used; each reason has its own message in the UI. */
export type ConnectionFailure =
  | 'invalid-url' // not an http(s) address
  | 'unreachable' // nothing answered (refused, unknown host, network down)
  | 'timeout' // no answer in time
  | 'not-ayna' // something answered, but not the AYNA health endpoint
  | 'db-down' // the AYNA server answered but cannot reach Neo4j

export interface ConnectionError {
  ok: false
  reason: ConnectionFailure
  /** The normalised URL that was tried; absent for `invalid-url`. */
  url?: string
}

export type ConnectionResult = { ok: true; url: string } | ConnectionError

/**
 * The local agent as the main process sees it:
 * `starting` (first launch) → `connected` ⇄ `restarting` (after a crash, up to the
 * restart limit) → `failed`; `stopped` once the app quits.
 */
export type AgentState = 'starting' | 'connected' | 'restarting' | 'failed' | 'stopped'

export interface AgentStatus {
  state: AgentState
  /** Restarts used since the agent was last stable; at most `maxRestarts`. */
  restarts: number
  maxRestarts: number
  /** Why the last launch failed (exit code, stderr tail, timeout), for `restarting` and `failed`. */
  detail?: string
}

/** `[left, top, right, bottom]` in physical pixels, virtual-screen coordinates (`docs/agent-rpc.md`). */
export type Bounds = [number, number, number, number]

/** A visible top-level window, as the agent's `listWindows` reports it. */
export interface WindowInfo {
  /** Native window handle; valid only while the window exists. */
  handle: number
  title: string
  className: string
  processId: number
  /** Null when the agent cannot read it (e.g. an elevated process). */
  processName: string | null
  bounds: Bounds
}

/** Why a call to the local agent failed. */
export type AgentFailure =
  | 'not-connected' // no agent running, or it stopped before answering
  | 'uia-unavailable' // the agent has no UI Automation backend (not Windows, or before #12)
  | 'timeout'
  | 'window-gone' // no window has that handle any more
  | 'snapshot-timeout' // the agent gave up the walk at its time budget
  | 'snapshot-version' // the snapshot is in a format this client does not read; `detail` names it
  | 'bad-response' // the answer does not match `docs/agent-rpc.md`
  | 'agent-error' // any other JSON-RPC error; `detail` has the agent's message

export type WindowsResult =
  { ok: true; windows: WindowInfo[] } | { ok: false; reason: AgentFailure; detail?: string }

export type SnapshotResult =
  { ok: true; snapshot: Snapshot } | { ok: false; reason: AgentFailure; detail?: string }

/** A screen point in physical pixels, virtual-screen coordinates (like `Bounds`). */
export interface ScreenPoint {
  x: number
  y: number
}

/** Whether the Spy's pick hotkey is active; `label` is the key combination to show. */
export interface PickHotkeyState {
  active: boolean
  label: string
}

export interface AynaApi {
  getAppInfo(): Promise<AppInfo>
  getSettings(): Promise<Settings>
  /** The UI language: the user's choice, else the first-run rule (`languageFor`). */
  getLanguage(): Promise<Language>
  /** Saves the user's choice of UI language, kept across restarts. */
  setLanguage(language: Language): Promise<void>
  /** Checks `url` against the server's health endpoint without saving it. */
  checkServer(url: string): Promise<ConnectionResult>
  /** Checks `url` and, only if the server answers, saves it as this machine's server. */
  connectServer(url: string): Promise<ConnectionResult>
  /** Lists the applications on the saved server, sorted by name. */
  listApplications(): Promise<ApplicationsResult>
  /** Creates an application on the saved server (does not choose it). */
  createApplication(name: string, technology: string): Promise<CreateApplicationResult>
  /** Saves `id` as this machine's chosen application. */
  chooseApplication(id: string): Promise<void>
  /** Versions of the application, as the server orders them. */
  listVersions(appId: string): Promise<VersionsResult>
  createVersion(appId: string, version: string): Promise<CreateVersionResult>
  /** Imports the capture under the version (once), then stores the object linked to the element. */
  addToRepository(object: NewRepoObject): Promise<AddToRepositoryResult>
  /** The application's repository objects by name, with their test counts. */
  listRepoObjects(appId: string): Promise<RepoObjectsResult>
  getRepoObject(id: string): Promise<RepoObjectResult>
  /** Renames the object or replaces how it is found; steps keep working (FR-08). */
  updateRepoObject(id: string, change: RepoObjectChange): Promise<RepoObjectResult>
  /** Refused with `in-use` while tests use the object (FR-09). */
  deleteRepoObject(id: string): Promise<RepoDeleteResult>
  /** The application's tests by name, with their step counts. */
  listTests(appId: string): Promise<TestsResult>
  /** A new test with no steps. */
  createTest(appId: string, name: string): Promise<TestResult>
  getTest(id: string): Promise<TestResult>
  renameTest(id: string, name: string): Promise<TestResult>
  deleteTest(id: string): Promise<TestDeleteResult>
  /** Replaces the test's steps; the answer has them as stored, with their ids. */
  saveSteps(id: string, document: StepDocument): Promise<TestResult>
  /** Checks `document` against `schemas/step.schema.json`; empty when it is valid. */
  validateSteps(document: StepDocument): Promise<StepProblem[]>
  getAgentStatus(): Promise<AgentStatus>
  /** Calls `listener` on every agent status change; returns a function that unsubscribes. */
  onAgentStatus(listener: (status: AgentStatus) => void): () => void
  /** Starts the agent again after it has `failed`, with a fresh restart budget. */
  retryAgent(): Promise<void>
  /** Lists the visible top-level windows through the agent, for the Spy. */
  listWindows(): Promise<WindowsResult>
  /**
   * Captures the UI Automation tree of the window with `handle` (from `listWindows`). With
   * `budgetMs` the agent may walk that long instead of its default 5 s.
   */
  snapshot(handle: number, budgetMs?: number): Promise<SnapshotResult>
  /**
   * Draws a frame around `bounds` on screen for a few seconds, above every window and
   * without taking focus or clicks; `null` removes it at once.
   */
  highlight(bounds: Bounds | null): Promise<void>
  /**
   * Turns the global pick hotkey on while the Spy is shown, and off again. `active` is false
   * when another program holds the key combination.
   */
  setPickHotkey(enabled: boolean): Promise<PickHotkeyState>
  /** Calls `listener` with the cursor position each time the pick hotkey is pressed. */
  onPick(listener: (point: ScreenPoint) => void): () => void
  /** Logs in to the saved server; the session lasts until logout, expiry or a server change. */
  login(username: string, password: string): Promise<LoginResult>
  /** Ends the session on the server (best effort) and forgets it. */
  logout(): Promise<void>
  /** The signed-in account, or null when there is no session. */
  currentUser(): Promise<CurrentUser | null>
  /** Admin only, like every user-management call below; a tester gets `forbidden`. */
  listUsers(): Promise<UsersResult>
  createUser(username: string, password: string, role: Role): Promise<UserResult>
  /** Changes the role, the password or both; a new password ends that account's sessions. */
  updateUser(id: string, change: { role?: Role; password?: string }): Promise<UserResult>
  /** The account can no longer log in; its name stays on what it did. */
  removeUser(id: string): Promise<DoneResult>
  listTokens(userId: string): Promise<TokensResult>
  createToken(userId: string, name: string): Promise<CreatedTokenResult>
  revokeToken(tokenId: string): Promise<DoneResult>
}

export const IPC = {
  getAppInfo: 'app:get-info',
  getSettings: 'settings:get',
  getLanguage: 'settings:get-language',
  setLanguage: 'settings:set-language',
  checkServer: 'server:check',
  connectServer: 'server:connect',
  listApplications: 'apps:list',
  createApplication: 'apps:create',
  chooseApplication: 'apps:choose',
  listVersions: 'versions:list',
  createVersion: 'versions:create',
  addToRepository: 'repository:add',
  listRepoObjects: 'repository:list',
  getRepoObject: 'repository:get',
  updateRepoObject: 'repository:update',
  deleteRepoObject: 'repository:delete',
  listTests: 'tests:list',
  createTest: 'tests:create',
  getTest: 'tests:get',
  renameTest: 'tests:rename',
  deleteTest: 'tests:delete',
  saveSteps: 'tests:save-steps',
  validateSteps: 'tests:validate-steps',
  getAgentStatus: 'agent:get-status',
  retryAgent: 'agent:retry',
  listWindows: 'spy:list-windows',
  snapshot: 'spy:snapshot',
  highlight: 'spy:highlight',
  setPickHotkey: 'spy:set-pick-hotkey',
  /** Main → renderer event, not a handler. */
  pick: 'spy:pick',
  /** Main → renderer event, not a handler. */
  agentStatus: 'agent:status',
  login: 'auth:login',
  logout: 'auth:logout',
  currentUser: 'auth:current-user',
  listUsers: 'users:list',
  createUser: 'users:create',
  updateUser: 'users:update',
  removeUser: 'users:remove',
  listTokens: 'tokens:list',
  createToken: 'tokens:create',
  revokeToken: 'tokens:revoke',
} as const
