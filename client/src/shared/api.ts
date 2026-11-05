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
  checkServer: 'server:check',
  connectServer: 'server:connect',
  listApplications: 'apps:list',
  createApplication: 'apps:create',
  chooseApplication: 'apps:choose',
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
