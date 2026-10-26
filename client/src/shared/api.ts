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
}

export const IPC = {
  getAppInfo: 'app:get-info',
  getSettings: 'settings:get',
  checkServer: 'server:check',
  connectServer: 'server:connect',
  listApplications: 'apps:list',
  createApplication: 'apps:create',
  chooseApplication: 'apps:choose',
} as const
