// Sample data for `npm run demo`. It goes through the real REST API, so it passes the same
// checks as the client. Running it again adds only what is missing and leaves the rest alone.
import { readFile } from 'node:fs/promises'
import { defaultSnapshot } from '../mock/fake-agent-env.mjs'

const APP = { name: 'AYNA Deneme Uygulaması', technology: 'PySide6' }

// The client opens on the last version, which has no capture yet: the demo captures it live.
const VERSIONS = ['1.0', '1.1']
const CAPTURED_VERSION = '1.0'

// Logical name → the element of `dev/mock/snapshot.json` it stands for.
const OBJECTS = {
  'login.userNameInput': 'e8',
  'login.passwordInput': 'e10',
  'login.rememberMeCheckBox': 'e11',
  'login.loginButton': 'e12',
  'login.statusLabel': 'e13',
}

const type = (target, value) => ({ keyword: 'Type', target, value })
const click = (target) => ({ keyword: 'Click', target })
const contains = (target, expected) => ({
  keyword: 'Verify',
  target,
  checkpoint: { property: 'name', operator: 'contains', expected },
})

const TESTS = {
  'Geçerli kullanıcıyla giriş': [
    { keyword: 'Wait', target: 'login.userNameInput', timeoutMs: 10000 },
    type('login.userNameInput', 'admin'),
    type('login.passwordInput', 'admin'),
    click('login.rememberMeCheckBox'),
    {
      keyword: 'Verify',
      target: 'login.rememberMeCheckBox',
      checkpoint: { property: 'checked', operator: 'equals', expected: true },
    },
    click('login.loginButton'),
    contains('login.statusLabel', 'Hoş geldiniz'),
  ],
  'Hatalı şifre uyarısı': [
    type('login.userNameInput', 'admin'),
    type('login.passwordInput', 'yanlis-sifre'),
    click('login.loginButton'),
    contains('login.statusLabel', 'hatalı'),
  ],
}

/** Calls the server; an unexpected answer becomes an error that names the call. */
function client(server, token) {
  return async (method, path, body) => {
    const response = await fetch(`${server}${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const text = await response.text()
    if (!response.ok) {
      throw new Error(`${method} ${path} answered ${response.status}: ${text.slice(0, 300)}`)
    }
    return text ? JSON.parse(text) : null
  }
}

/** Finds the item with this value in `key`, or creates it. */
async function ensure(items, key, value, create) {
  return items.find((item) => item[key] === value) ?? (await create())
}

/** Adds what is missing. Returns the application, so the client can open on it. */
export async function seed(server, token) {
  const api = client(server, token)

  const apps = await api('GET', '/api/apps')
  const app = await ensure(apps, 'name', APP.name, () => api('POST', '/api/apps', APP))

  const versionsPath = `/api/apps/${app.id}/versions`
  const versions = await api('GET', versionsPath)
  const known = []
  for (const version of VERSIONS) {
    known.push(
      await ensure(versions, 'version', version, () => api('POST', versionsPath, { version })),
    )
  }
  const captured = known.find((version) => version.version === CAPTURED_VERSION)

  // The same snapshot id into the same version answers 200 and writes nothing.
  const snapshot = JSON.parse(await readFile(defaultSnapshot, 'utf8'))
  await api('POST', `${versionsPath}/${captured.id}/snapshots`, snapshot)

  const objectsPath = `/api/apps/${app.id}/repo-objects`
  const objects = await api('GET', objectsPath)
  for (const [name, elementId] of Object.entries(OBJECTS)) {
    const { element } = snapshot.elements.find((node) => node.id === elementId)
    await ensure(objects, 'name', name, () =>
      api('POST', objectsPath, {
        name,
        snapshotId: snapshot.snapshotId,
        snapshotElementId: elementId,
        primary: { automationId: element.automationId },
        fallback: { controlType: element.controlType },
      }),
    )
  }

  const testsPath = `/api/apps/${app.id}/tests`
  const tests = await api('GET', testsPath)
  for (const [name, steps] of Object.entries(TESTS)) {
    await ensure(tests, 'name', name, async () => {
      const test = await api('POST', testsPath, { name })
      return api('PUT', `/api/tests/${test.id}/steps`, { version: snapshot.version, steps })
    })
  }

  return app
}
