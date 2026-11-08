import type {
  AddToRepositoryResult,
  AgentFailure,
  AgentState,
  ConnectionFailure,
  LoginResult,
  RequestFailure,
  Role,
  UsersError,
} from '../../shared/api.ts'
import type { ElementDescriptor, ElementField } from '../../shared/element.ts'
import type { NameProblem, PropertyUse } from '../../shared/repository.ts'

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

  spyTitle: 'Object Spy',
  spyIntro: 'Choose a window to see its properties and where it is on screen.',
  spyRefresh: 'Refresh',
  spyEmpty: 'The agent sees no open windows.',
  spyNoTitle: '(no title)',
  spyUnknownProcess: 'unknown process',
  spyTreeTitle: 'Elements',
  spyCapturing: 'Capturing the window…',
  spyCaptureAgain: 'Capture again',
  /** `app` is the exe name and file version, when the agent could read them. */
  spyCaptured: (time: string, app: string | undefined, count: number, durationMs: number) =>
    `Captured at ${time}${app ? ` from ${app}` : ''}: ` +
    `${count} ${count === 1 ? 'element' : 'elements'} in ${durationMs} ms.`,
  spyReadErrors: (count: number) =>
    `${count} ${count === 1 ? 'property' : 'properties'} could not be read, so some values are missing.`,
  spyUnknownControlType: 'Element',
  spyExpand: 'Expand',
  spyCollapse: 'Collapse',
  spyHotkeyHint: (label: string) => `Press ${label} with the mouse over an element to pick it.`,
  spyHotkeyTaken: (label: string) =>
    `${label} is in use by another program, so picking with the keyboard is off.`,
  spyPicked: (x: number, y: number) =>
    `Picked the point ${x}, ${y}. Finding the element under it needs a newer agent.`,
  spyPropertiesTitle: 'Properties',
  spyWindowOnly: 'From the window list only, because the window could not be captured.',
  spyNotCaptured: 'not captured',
  spyYes: 'yes',
  spyNo: 'no',
  // Labels follow the descriptor's UIA names, which testers know from other spy tools.
  spyProperties: {
    automationId: 'AutomationId',
    name: 'Name',
    controlType: 'Control type',
    className: 'Class name',
    frameworkId: 'Framework',
    bounds: 'Bounds (px)',
    dpi: 'DPI',
    parentPath: 'Parent path',
    siblingIndex: 'Sibling index',
    nearestLabel: 'Nearest label',
    nearestLabelSource: 'Label found by',
    windowTitle: 'Window title',
    enabled: 'Enabled',
    offscreen: 'Off screen',
    helpText: 'Help text',
    accessKey: 'Access key',
    nativeWindowHandle: 'Window handle',
  } satisfies Record<ElementField, string>,
  spyLabelSources: {
    labeledBy: 'LabeledBy relation',
    geometric: 'nearest label beside it',
    parentRow: 'nearest label in the parent row',
  } satisfies Record<NonNullable<ElementDescriptor['nearestLabelSource']>, string>,
  agentErrors: {
    'not-connected': () => 'The agent is not running. Wait for it to connect, then refresh.',
    'uia-unavailable': () =>
      'UI Automation is not available on this machine. The Spy works on Windows only.',
    timeout: () => 'The agent did not answer in time. Refresh to try again.',
    'window-gone': () => 'The window has closed. Refresh the list.',
    'snapshot-timeout': () =>
      'Capturing the window took too long, so the agent stopped. The application may be busy; capture again.',
    'bad-response': () => 'The agent answered with something unexpected.',
    'agent-error': (detail?: string) =>
      detail ? `The agent reported an error: ${detail}` : 'The agent reported an error.',
  } satisfies Record<AgentFailure, (detail?: string) => string>,

  repoAdd: 'Add to repository',
  repoTitle: 'Add to the object repository',
  repoNameLabel: 'Name',
  repoNamePlaceholder: 'login.userNameInput',
  repoNameHint:
    'Tests use this name for the element. Write the screen, a dot, then the element: login.userNameInput, login.okButton.',
  repoNameProblems: {
    blank: 'Enter a name.',
    form: 'Write the name as screen.element: two words joined by a dot, each starting with a small letter, e.g. login.userNameInput.',
    reserved: '"none.noMatch" is reserved for the AI service. Choose another name.',
  } satisfies Record<NameProblem, string>,
  repoNoVersion: 'Choose the application version at the top of the Spy first.',
  repoFoundBy: 'How AYNA finds it',
  repoBackup: (labels: string[]) =>
    `If the application changes, it also tries: ${labels.join(', ')}.`,
  repoAdvanced: 'Advanced settings',
  repoAdvancedHint:
    'AYNA looks for the element with the "Find by" properties. If they stop matching after the application changes, it tries the "Backup" ones. Values can be edited.',
  repoPropertyHeader: 'Property',
  repoValueHeader: 'Value',
  repoUseHeader: 'Use',
  repoUses: {
    primary: 'Find by',
    fallback: 'Backup',
    unused: "Don't use",
  } satisfies Record<PropertyUse, string>,
  repoNoPrimary: 'Choose at least one property to find the element by, under Advanced settings.',
  repoEmptyValue: (property: string) => `${property} needs a value, or set it to "Don't use".`,
  repoNotInteger: (property: string) => `${property} must be a whole number of 0 or more.`,
  repoMatches: (count: number) =>
    count === 1
      ? 'Only this element matches.'
      : count === 0
        ? 'No element in the capture matches. Check the values under Advanced settings.'
        : `${count} elements in the capture match. Under Advanced settings, set one more property to "Find by".`,
  repoSave: 'Save',
  repoSaving: 'Saving…',
  repoCancel: 'Cancel',
  repoSaved: (name: string) => `Saved ${name} in the object repository.`,
  repoErrors: {
    'no-server': 'No server is set. Connect to a server first.',
    unreachable: 'Could not reach the server. Check that it is running.',
    timeout: 'The server did not answer in time.',
    unauthorized: 'Your session has ended. Log in again.',
    'bad-response': 'The server answered with something unexpected.',
    duplicate: 'This logical name is already used in this application.',
    invalid: 'The server did not accept the object.',
    'not-found': 'The application or version no longer exists on the server.',
    'snapshot-conflict':
      'This capture is already stored under another version. Capture the window again to store it under this one.',
  } satisfies Record<Extract<AddToRepositoryResult, { ok: false }>['reason'], string>,
  versionLabel: 'Application version',
  versionNone:
    'Which version of the application are you testing? Add it, and saved elements are stored under it.',
  versionNew: 'New version',
  versionNewLabel: 'New version',
  versionPlaceholder: 'e.g. 1.0',
  versionAdd: 'Add',
  versionRetry: 'Try again',
  versionErrors: {
    'no-server': 'No server is set. Connect to a server first.',
    unreachable: 'Could not reach the server. Check that it is running.',
    timeout: 'The server did not answer within 5 seconds.',
    unauthorized: 'Your session has ended. Log in again.',
    'bad-response': 'The server answered with something unexpected.',
    duplicate: 'This version already exists. Choose it from the list.',
    invalid: 'Enter a version.',
    'not-found': 'The application no longer exists on the server.',
  } satisfies Record<RequestFailure | 'duplicate' | 'invalid' | 'not-found', string>,

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
