// Contract between the preload bridge and the renderer. The renderer only ever
// sees `window.ayna`, shaped like `AynaApi`; every method maps to one IPC channel.

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
}

/** An application under test, as the server's `/api/apps` returns it. */
export interface Application {
  id: string
  name: string
  technology: string
}

/** Why a request to the saved server failed. */
export type RequestFailure =
  | 'no-server' // no server saved yet
  | 'unreachable'
  | 'timeout'
  | 'bad-response' // the server answered with something unexpected

export type ApplicationsResult =
  { ok: true; apps: Application[] } | { ok: false; reason: RequestFailure }

export type CreateApplicationResult =
  { ok: true; app: Application } | { ok: false; reason: RequestFailure | 'duplicate' | 'invalid' }

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
  | 'bad-response' // the answer does not match `docs/agent-rpc.md`
  | 'agent-error' // any other JSON-RPC error; `detail` has the agent's message

export type WindowsResult =
  { ok: true; windows: WindowInfo[] } | { ok: false; reason: AgentFailure; detail?: string }

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
  getAgentStatus(): Promise<AgentStatus>
  /** Calls `listener` on every agent status change; returns a function that unsubscribes. */
  onAgentStatus(listener: (status: AgentStatus) => void): () => void
  /** Starts the agent again after it has `failed`, with a fresh restart budget. */
  retryAgent(): Promise<void>
  /** Lists the visible top-level windows through the agent, for the Spy. */
  listWindows(): Promise<WindowsResult>
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
}

export const IPC = {
  getAppInfo: 'app:get-info',
  getSettings: 'settings:get',
  checkServer: 'server:check',
  connectServer: 'server:connect',
  listApplications: 'apps:list',
  createApplication: 'apps:create',
  chooseApplication: 'apps:choose',
  getAgentStatus: 'agent:get-status',
  retryAgent: 'agent:retry',
  listWindows: 'spy:list-windows',
  highlight: 'spy:highlight',
  setPickHotkey: 'spy:set-pick-hotkey',
  /** Main → renderer event, not a handler. */
  pick: 'spy:pick',
  /** Main → renderer event, not a handler. */
  agentStatus: 'agent:status',
} as const
