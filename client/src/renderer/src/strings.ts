import type {
  AgentState,
  ConnectionFailure,
  LoginResult,
  RequestFailure,
  Role,
  UsersError,
} from '../../shared/api.ts'

// All UI text in one place, for later translation.
export const strings = {
  appName: 'AYNA',
  tagline: 'Codeless UI test automation for Windows desktop apps',
  loading: 'Loading…',
  bridgeError: 'Could not reach the main process.',
  versionsTitle: 'Runtime',

  serverTitle: 'Server connection',
  serverIntro: 'Enter the address of the AYNA server on your network.',
  serverUrlLabel: 'Server URL',
  serverUrlPlaceholder: 'http://ayna-server:8080',
  connect: 'Connect',
  connecting: 'Connecting…',
  changeServer: 'Change server',
  cancel: 'Cancel',
  checkingSaved: (url: string) => `Connecting to ${url}…`,
  connectedTo: (url: string) => `Connected to ${url}`,
  connectionErrors: {
    'invalid-url': () =>
      'Enter an http:// or https:// address, for example http://ayna-server:8080.',
    unreachable: (url?: string) =>
      `Could not reach ${url}. Check the address and that the server is running.`,
    timeout: (url?: string) => `${url} did not answer within 5 seconds.`,
    'not-ayna': (url?: string) => `${url} answered, but it is not an AYNA server.`,
    'db-down': (url?: string) =>
      `The AYNA server at ${url} is running but cannot reach its database.`,
  } satisfies Record<ConnectionFailure, (url?: string) => string>,

  appsTitle: 'Application under test',
  appsIntro: 'Choose the application you want to test on this machine.',
  appsEmpty: 'There are no applications on this server yet. Add the first one below.',
  appsMissing: 'The application chosen before no longer exists on this server. Choose another.',
  appsRetry: 'Try again',
  changeApplication: 'Change application',
  testingApp: (name: string, technology: string) => `Testing ${name} (${technology})`,
  newAppTitle: 'New application',
  appNameLabel: 'Name',
  appNamePlaceholder: 'Notepad',
  appTechnologyLabel: 'Technology',
  appTechnologyPlaceholder: 'Win32, WinForms, WPF…',
  createApp: 'Add and choose',
  creatingApp: 'Adding…',
  requestErrors: {
    'no-server': 'No server is set. Connect to a server first.',
    unreachable: 'Could not reach the server. Check that it is running.',
    timeout: 'The server did not answer within 5 seconds.',
    unauthorized: 'Your session has ended. Log in again.',
    'bad-response': 'The server answered with something unexpected.',
    duplicate: 'An application with this name already exists. Choose it from the list.',
    invalid: 'Enter both a name and a technology.',
  } satisfies Record<RequestFailure | 'duplicate' | 'invalid', string>,
  chooseFailed:
    'Could not save the choice on this machine. Check that the settings folder is writable.',

  agentLabel: 'Agent',
  agentStates: {
    starting: 'starting…',
    connected: 'connected',
    restarting: 'restarting…',
    failed: 'failed',
    stopped: 'stopped',
  } satisfies Record<AgentState, string>,
  agentAttempt: (restarts: number, max: number) => `attempt ${restarts} of ${max}`,
  agentRetry: 'Start again',

  loginTitle: 'Log in',
  loginIntro: (url: string) => `Log in to the AYNA server at ${url}.`,
  usernameLabel: 'User name',
  passwordLabel: 'Password',
  logIn: 'Log in',
  loggingIn: 'Logging in…',
  logOut: 'Log out',
  sessionEnded: 'Your session has ended. Log in again.',
  signedInAs: (username: string, role: string) => `Logged in as ${username} (${role})`,
  loginErrors: {
    'wrong-credentials': 'Wrong user name or password.',
    'no-server': 'No server is set. Connect to a server first.',
    unreachable: 'Could not reach the server. Check that it is running.',
    timeout: 'The server did not answer within 5 seconds.',
    unauthorized: 'Wrong user name or password.',
    'bad-response': 'The server answered with something unexpected.',
  } satisfies Record<Extract<LoginResult, { ok: false }>['reason'], string>,

  manageUsers: 'Manage users',
  usersTitle: 'Users',
  usersIntro: 'Accounts that can log in to this server. Only admins manage them.',
  usersAdminOnly: 'Only admins manage users. Ask an admin to change your account.',
  usersBack: 'Back',
  usersRetry: 'Try again',
  you: '(you)',
  roles: { admin: 'Admin', tester: 'Tester' } satisfies Record<Role, string>,
  roleLabel: 'Role',
  createdOn: (date: string) => `since ${date}`,
  newUserTitle: 'New user',
  newUserHint: 'User names use a-z, digits, ".", "_" or "-". Passwords need at least 8 characters.',
  createUser: 'Add user',
  userCreated: (username: string) => `Added ${username}.`,
  roleChanged: (username: string, role: string) => `${username} is now ${role}.`,
  setPassword: 'Set password',
  newPasswordLabel: (username: string) => `New password for ${username}`,
  savePassword: 'Save password',
  passwordChanged: (username: string) =>
    `Password of ${username} changed. Their open sessions have ended.`,
  removeUser: 'Remove',
  confirmRemove: (username: string) =>
    `Remove ${username}? They can no longer log in; their name stays on what they did.`,
  confirmRemoveButton: 'Yes, remove',
  userRemoved: (username: string) => `Removed ${username}.`,
  tokens: 'API tokens',
  tokensTitle: (username: string) => `API tokens of ${username}`,
  tokensIntro: 'For a CI service that runs tests without logging in (Authorization: Bearer).',
  tokensEmpty: 'No API tokens yet.',
  tokenNameLabel: 'Token name',
  tokenNamePlaceholder: 'jenkins',
  createToken: 'Create token',
  // The permission handler denies clipboard access, so the admin selects and copies by hand.
  tokenSecret: (name: string) =>
    `Token "${name}": select and copy it now; it will not be shown again.`,
  revokeToken: 'Revoke',
  hide: 'Hide',
  usersErrors: {
    'no-server': 'No server is set. Connect to a server first.',
    unreachable: 'Could not reach the server. Check that it is running.',
    timeout: 'The server did not answer within 5 seconds.',
    unauthorized: 'Your session has ended. Log in again.',
    'bad-response': 'The server answered with something unexpected.',
    forbidden: 'Only admins manage users.',
    'not-found': 'This account or token no longer exists. Reload the list.',
    invalid: 'The server did not accept these values.',
    conflict: 'The server refused the change.',
  } satisfies Record<UsersError['reason'], string>,
} as const

/** The server's own message when it sent one (e.g. which field is wrong), else ours. */
export function usersErrorText(error: UsersError): string {
  return error.detail ?? strings.usersErrors[error.reason]
}
