// Sample data for `npm run demo`. It goes through the real REST API, so it passes the same
// checks as the client. Running it again adds what is missing and puts the sample objects'
// property sets and the two sample tests back as they were, so a rehearsal leaves nothing
// behind in them.
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { defaultSnapshot } from '../mock/fake-agent-env.mjs'

const STEP_SCHEMA = new URL('../../../schemas/step.schema.json', import.meta.url)

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

// The texts are the ones `eval/apps/trial/app.py` really shows.
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
    contains('login.statusLabel', 'Welcome'),
  ],
  'Hatalı şifre uyarısı': [
    type('login.userNameInput', 'admin'),
    type('login.passwordInput', 'yanlis-sifre'),
    click('login.loginButton'),
    contains('login.statusLabel', 'Invalid'),
  ],
}

/**
 * The objects to add, as the server takes them. Primary is the AutomationId. The backup set
 * must find exactly one element too, or using it would be a failure rather than a repair
 * (#40, #207): `name` + `controlType` does that in the trial window. `statusLabel` has no
 * Name, so it keeps only its primary set.
 */
export function repoObjects(snapshot) {
  return Object.entries(OBJECTS).map(([name, elementId]) => {
    const { element } = snapshot.elements.find((node) => node.id === elementId)
    const fallback =
      element.name === undefined ? {} : { name: element.name, controlType: element.controlType }
    return {
      name,
      snapshotId: snapshot.snapshotId,
      snapshotElementId: elementId,
      primary: { automationId: element.automationId },
      fallback,
    }
  })
}

/**
 * The server takes a snapshot id into one version only, and a database that was used before
 * may hold the fixture's id already. So the sample capture gets an id of its own, which stays
 * the same on every run for this version.
 */
function snapshotIdFor(versionId) {
  const hex = createHash('sha256').update(`ayna-demo:${versionId}`).digest('hex')
  const part = (from, to) => hex.slice(from, to)
  return `${part(0, 8)}-${part(8, 12)}-4${part(13, 16)}-8${part(17, 20)}-${part(20, 32)}`
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
  const fixture = JSON.parse(await readFile(defaultSnapshot, 'utf8'))
  const snapshot = { ...fixture, snapshotId: snapshotIdFor(captured.id) }
  await api('POST', `${versionsPath}/${captured.id}/snapshots`, snapshot)

  const objectsPath = `/api/apps/${app.id}/repo-objects`
  const objects = await api('GET', objectsPath)
  for (const object of repoObjects(snapshot)) {
    const saved = objects.find((item) => item.name === object.name)
    if (!saved) {
      await api('POST', objectsPath, object)
    } else {
      // An older seed or a rehearsal may have changed the sets: put them back.
      const { primary, fallback } = object
      await api('PATCH', `/api/repo-objects/${saved.id}`, { primary, fallback })
    }
  }

  // The step schema's own version, not the snapshot's: the server accepts only that one.
  const stepSchema = JSON.parse(await readFile(STEP_SCHEMA, 'utf8'))
  const testsPath = `/api/apps/${app.id}/tests`
  const tests = await api('GET', testsPath)
  for (const [name, steps] of Object.entries(TESTS)) {
    const test = await ensure(tests, 'name', name, () => api('POST', testsPath, { name }))
    const version = stepSchema.properties.version.const
    await api('PUT', `/api/tests/${test.id}/steps`, { version, steps })
  }

  return app
}
