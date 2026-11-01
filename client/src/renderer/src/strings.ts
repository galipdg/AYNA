import type {
  AgentFailure,
  AgentState,
  ConnectionFailure,
  RequestFailure,
} from '../../shared/api.ts'
import type { ElementDescriptor, ElementField } from '../../shared/element.ts'

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
  spyTreePending: 'The element tree appears here once the agent can capture windows.',
  spyHotkeyHint: (label: string) => `Press ${label} with the mouse over an element to pick it.`,
  spyHotkeyTaken: (label: string) =>
    `${label} is in use by another program, so picking with the keyboard is off.`,
  spyPicked: (x: number, y: number) =>
    `Picked the point ${x}, ${y}. Finding the element under it needs a newer agent.`,
  spyPropertiesTitle: 'Properties',
  spyWindowOnly:
    'From the window list only. The other properties appear once the agent can capture windows.',
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
    'bad-response': () => 'The agent answered with something unexpected.',
    'agent-error': (detail?: string) =>
      detail ? `The agent reported an error: ${detail}` : 'The agent reported an error.',
  } satisfies Record<AgentFailure, (detail?: string) => string>,
} as const
