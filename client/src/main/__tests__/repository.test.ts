import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { join } from 'node:path'
import { after, before, describe, it } from 'node:test'
import type { NewRepoObject } from '../../shared/api.ts'
import type { Snapshot } from '../../shared/snapshot.ts'
import { addToRepository, createVersion, listVersions } from '../repository.ts'

const snapshot: Snapshot = JSON.parse(
  readFileSync(
    join(
      import.meta.dirname,
      '..',
      '..',
      '..',
      '..',
      'schemas',
      'examples',
      'snapshot',
      'trial-login.json',
    ),
    'utf8',
  ),
)

const object: NewRepoObject = {
  appId: 'a1',
  versionId: 'v1',
  snapshot,
  snapshotElementId: 'e8',
  name: 'login.userNameInput',
  primary: { automationId: 'QApplication.loginWindow.usernameInput' },
  fallback: { name: 'Username', controlType: 'Edit' },
}

const stored = {
  id: 'o1',
  appId: 'a1',
  name: 'login.userNameInput',
  primary: object.primary,
  fallback: object.fallback,
  resolvesTo: [
    {
      appVersionId: 'v1',
      elementId: 'x',
      snapshotId: snapshot.snapshotId,
      snapshotElementId: 'e8',
    },
  ],
  createdBy: { id: 'u1', username: 'tester' },
  createdAt: '2026-11-03T10:00:00Z',
}

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('versions and repository API', () => {
  let server: Server
  let base: string
  let handle: (req: IncomingMessage, body: string, res: ServerResponse) => void

  before(async () => {
    server = createServer((req, res) => {
      let body = ''
      req.on('data', (chunk) => (body += chunk))
      req.on('end', () => handle(req, body, res))
    })
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`
  })

  after(() => {
    server.closeAllConnections()
    server.close()
  })

  function json(res: ServerResponse, status: number, body: unknown) {
    res.writeHead(status, { 'content-type': 'application/json' }).end(JSON.stringify(body))
  }

  function problem(status: number, detail: string, errors?: unknown[]) {
    return { type: 'about:blank', status, detail, ...(errors ? { errors } : {}) }
  }

  describe('listVersions and createVersion', () => {
    it('lists the versions of one application, with the session token', async () => {
      let request = ''
      handle = (req, _body, res) => {
        request = `${req.method} ${req.url} ${req.headers.authorization}`
        json(res, 200, [{ id: 'v1', version: '1.0' }])
      }
      assert.deepEqual(await listVersions(base, 'a 1', { token: 't' }), {
        ok: true,
        versions: [{ id: 'v1', version: '1.0' }],
      })
      assert.equal(request, 'GET /api/apps/a%201/versions Bearer t')
    })

    it('creates a version and maps 409 to duplicate with the server message', async () => {
      let body = ''
      handle = (_req, sent, res) => {
        body = sent
        json(res, 201, { id: 'v2', version: '1.1' })
      }
      assert.deepEqual(await createVersion(base, 'a1', '1.1'), {
        ok: true,
        version: { id: 'v2', version: '1.1' },
      })
      assert.equal(body, '{"version":"1.1"}')

      handle = (_req, _body, res) => json(res, 409, problem(409, 'Version 1.1 already exists'))
      assert.deepEqual(await createVersion(base, 'a1', '1.1'), {
        ok: false,
        reason: 'duplicate',
        detail: 'Version 1.1 already exists',
      })
    })
  })

  describe('addToRepository', () => {
    it('imports the snapshot under the version, then creates the object', async () => {
      const requests: string[] = []
      const bodies: unknown[] = []
      handle = (req, body, res) => {
        requests.push(`${req.method} ${req.url}`)
        bodies.push(JSON.parse(body))
        if (req.url!.endsWith('/snapshots')) return json(res, 201, { windowId: 'w1' })
        json(res, 201, stored)
      }
      assert.deepEqual(await addToRepository(base, object), {
        ok: true,
        object: {
          id: 'o1',
          name: 'login.userNameInput',
          primary: object.primary,
          fallback: object.fallback,
        },
      })
      assert.deepEqual(requests, [
        'POST /api/apps/a1/versions/v1/snapshots',
        'POST /api/apps/a1/repo-objects',
      ])
      assert.deepEqual(bodies[0], snapshot)
      assert.deepEqual(bodies[1], {
        name: 'login.userNameInput',
        snapshotId: snapshot.snapshotId,
        snapshotElementId: 'e8',
        primary: object.primary,
        fallback: object.fallback,
      })
    })

    it('goes on when the snapshot was already imported into the version (200)', async () => {
      handle = (req, _body, res) =>
        req.url!.endsWith('/snapshots')
          ? json(res, 200, { windowId: 'w1' })
          : json(res, 201, stored)
      assert.equal((await addToRepository(base, object)).ok, true)
    })

    it('stops with snapshot-conflict when the capture belongs to another version', async () => {
      let created = false
      handle = (req, _body, res) => {
        if (req.url!.endsWith('/snapshots')) {
          return json(res, 409, problem(409, 'Snapshot s was already imported into version v0'))
        }
        created = true
        json(res, 201, stored)
      }
      assert.deepEqual(await addToRepository(base, object), {
        ok: false,
        reason: 'snapshot-conflict',
        detail: 'Snapshot s was already imported into version v0',
      })
      assert.equal(created, false)
    })

    it('reports a taken name as duplicate, with the message that names the existing object', async () => {
      const detail =
        'The logical name login.userNameInput is already used by repository object o0 in this application'
      handle = (req, _body, res) =>
        req.url!.endsWith('/snapshots') ? json(res, 201, {}) : json(res, 409, problem(409, detail))
      assert.deepEqual(await addToRepository(base, object), {
        ok: false,
        reason: 'duplicate',
        detail,
      })
    })

    it('passes on the fields the server refused', async () => {
      const errors = [
        { path: '$.primary.bounds', message: "'bounds' cannot identify an element" },
        { bad: true },
      ]
      handle = (req, _body, res) =>
        req.url!.endsWith('/snapshots')
          ? json(res, 201, {})
          : json(res, 400, problem(400, 'The repository object is not valid', errors))
      assert.deepEqual(await addToRepository(base, object), {
        ok: false,
        reason: 'invalid',
        detail: 'The repository object is not valid',
        fields: [errors[0]],
      })
    })

    it('reports unauthorized and bad-response like the other calls', async () => {
      handle = (_req, _body, res) => json(res, 401, {})
      assert.deepEqual(await addToRepository(base, object), { ok: false, reason: 'unauthorized' })
      handle = (req, _body, res) =>
        req.url!.endsWith('/snapshots') ? json(res, 201, {}) : json(res, 201, { id: 'o1' })
      assert.deepEqual(await addToRepository(base, object), { ok: false, reason: 'bad-response' })
    })
  })
})
