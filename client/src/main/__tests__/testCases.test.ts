import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import { STEP_SCHEMA_VERSION, type StepDocument } from '../../shared/steps.ts'
import { createTest, deleteTest, getTest, listTests, renameTest, saveSteps } from '../testCases.ts'

const document: StepDocument = {
  version: STEP_SCHEMA_VERSION,
  steps: [
    {
      id: '62b637f6-79e5-475f-9668-bd444c7ae20d',
      keyword: 'Type',
      target: 'login.usernameInput',
      value: 'admin',
    },
  ],
}

/** A test as the server's `TestResponse` sends it (#39). */
const stored = {
  id: 't1',
  appId: 'a1',
  name: 'Login works',
  document,
  createdBy: { id: 'u1', username: 'tester' },
  createdAt: '2026-11-04T10:00:00Z',
  updatedBy: { id: 'u2', username: 'ayse' },
  updatedAt: '2026-11-04T11:00:00Z',
}

const test = {
  id: 't1',
  name: 'Login works',
  document,
  updatedBy: 'ayse',
  updatedAt: '2026-11-04T11:00:00Z',
}

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('tests API', () => {
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

  it('lists the tests of one application, with the session token', async () => {
    let request = ''
    handle = (req, _body, res) => {
      request = `${req.method} ${req.url} ${req.headers.authorization}`
      json(res, 200, [{ id: 't1', name: 'Login works', stepCount: 6 }])
    }
    assert.deepEqual(await listTests(base, 'a 1', { token: 't' }), {
      ok: true,
      tests: [{ id: 't1', name: 'Login works', stepCount: 6 }],
    })
    assert.equal(request, 'GET /api/apps/a%201/tests Bearer t')
  })

  it('creates a test and maps 409 to duplicate with the server message', async () => {
    let sent = ''
    handle = (req, body, res) => {
      sent = `${req.method} ${req.url} ${body}`
      json(res, 201, stored)
    }
    assert.deepEqual(await createTest(base, 'a1', 'Login works'), { ok: true, test })
    assert.equal(sent, 'POST /api/apps/a1/tests {"name":"Login works"}')

    const detail = 'A test with this name already exists in the application: Login works'
    handle = (_req, _body, res) => json(res, 409, problem(409, detail))
    assert.deepEqual(await createTest(base, 'a1', 'Login works'), {
      ok: false,
      reason: 'duplicate',
      detail,
    })
  })

  it('reads one test, and maps 404 to not-found', async () => {
    handle = (req, _body, res) =>
      req.url === '/api/tests/t1' ? json(res, 200, stored) : json(res, 404, problem(404, 'x'))
    assert.deepEqual(await getTest(base, 't1'), { ok: true, test })
    assert.deepEqual(await getTest(base, 't2'), { ok: false, reason: 'not-found', detail: 'x' })
  })

  it('renames with PATCH and deletes with DELETE', async () => {
    const requests: string[] = []
    handle = (req, body, res) => {
      requests.push(`${req.method} ${req.url} ${body}`)
      if (req.method === 'DELETE') return res.writeHead(204).end()
      json(res, 200, { ...stored, name: 'Login' })
    }
    assert.deepEqual(await renameTest(base, 't1', 'Login'), {
      ok: true,
      test: { ...test, name: 'Login' },
    })
    assert.deepEqual(await deleteTest(base, 't1'), { ok: true })
    assert.deepEqual(requests, ['PATCH /api/tests/t1 {"name":"Login"}', 'DELETE /api/tests/t1 '])
  })

  it('saves the steps with PUT and returns them as stored', async () => {
    let sent: unknown
    handle = (req, body, res) => {
      sent = { request: `${req.method} ${req.url}`, body: JSON.parse(body) }
      json(res, 200, stored)
    }
    const fresh: StepDocument = {
      version: STEP_SCHEMA_VERSION,
      steps: [{ keyword: 'Type', target: 'login.usernameInput', value: 'admin' }],
    }
    assert.deepEqual(await saveSteps(base, 't1', fresh), { ok: true, test })
    assert.deepEqual(sent, { request: 'PUT /api/tests/t1/steps', body: fresh })
  })

  it('passes on the fields the server refused', async () => {
    const errors = [
      {
        path: '$.steps[0].target',
        message: "No repository object named 'login.gone' in this application",
      },
    ]
    const detail = 'The steps refer to unknown step ids or repository objects'
    handle = (_req, _body, res) => json(res, 400, problem(400, detail, errors))
    assert.deepEqual(await saveSteps(base, 't1', document), {
      ok: false,
      reason: 'invalid',
      detail,
      fields: errors,
    })
  })

  it('calls an answer of the wrong shape a bad response', async () => {
    handle = (_req, _body, res) => json(res, 200, { id: 't1' })
    assert.deepEqual(await getTest(base, 't1'), { ok: false, reason: 'bad-response' })
  })
})
