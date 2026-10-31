import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import {
  createToken,
  createUser,
  listTokens,
  listUsers,
  removeUser,
  revokeToken,
  updateUser,
} from '../users.ts'

const ayse = { id: 'u2', username: 'ayse', role: 'tester', createdAt: '2026-10-31T10:00:00Z' }
const ci = { id: 't1', name: 'jenkins', createdAt: '2026-10-31T11:00:00Z' }

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('users API', () => {
  let server: Server
  let base: string
  let handle: (req: IncomingMessage, body: string, res: ServerResponse) => void
  let seen: { request: string; authorization?: string; body?: unknown }

  before(async () => {
    server = createServer((req, res) => {
      let body = ''
      req.on('data', (chunk) => (body += chunk))
      req.on('end', () => {
        seen = {
          request: `${req.method} ${req.url}`,
          authorization: req.headers.authorization,
          body: body ? JSON.parse(body) : undefined,
        }
        handle(req, body, res)
      })
    })
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`
  })

  after(() => {
    server.closeAllConnections()
    server.close()
  })

  function answer(status: number, body?: unknown) {
    handle = (_req, _body, res) => {
      if (body === undefined) return res.writeHead(status).end()
      res.writeHead(status, { 'content-type': 'application/json' }).end(JSON.stringify(body))
    }
  }

  const options = { token: 't0k3n' }

  it('lists the accounts with the session token, keeping only known fields', async () => {
    answer(200, [{ ...ayse, passwordHash: 'x' }])
    assert.deepEqual(await listUsers(base, options), { ok: true, users: [ayse] })
    assert.equal(seen.request, 'GET /api/users')
    assert.equal(seen.authorization, 'Bearer t0k3n')
  })

  it('creates an account', async () => {
    answer(201, ayse)
    assert.deepEqual(await createUser(base, 'ayse', 'pw-12345678', 'tester', options), {
      ok: true,
      user: ayse,
    })
    assert.equal(seen.request, 'POST /api/users')
    assert.deepEqual(seen.body, { username: 'ayse', password: 'pw-12345678', role: 'tester' })
  })

  it('sends only the fields that change', async () => {
    answer(200, { ...ayse, role: 'admin' })
    const result = await updateUser(base, 'u2', { role: 'admin' }, options)
    assert.deepEqual(result, { ok: true, user: { ...ayse, role: 'admin' } })
    assert.equal(seen.request, 'PATCH /api/users/u2')
    assert.deepEqual(seen.body, { role: 'admin' })
  })

  it('removes an account and revokes a token on a 204', async () => {
    answer(204)
    assert.deepEqual(await removeUser(base, 'u2', options), { ok: true })
    assert.equal(seen.request, 'DELETE /api/users/u2')
    assert.deepEqual(await revokeToken(base, 't1', options), { ok: true })
    assert.equal(seen.request, 'DELETE /api/tokens/t1')
  })

  it('escapes ids in the path', async () => {
    answer(204)
    await removeUser(base, '../apps', options)
    assert.equal(seen.request, 'DELETE /api/users/..%2Fapps')
  })

  it('lists and creates API tokens; the secret comes back once', async () => {
    answer(200, [ci])
    assert.deepEqual(await listTokens(base, 'u2', options), { ok: true, tokens: [ci] })
    assert.equal(seen.request, 'GET /api/users/u2/tokens')

    answer(201, { ...ci, token: 's3cret' })
    assert.deepEqual(await createToken(base, 'u2', 'jenkins', options), {
      ok: true,
      token: ci,
      secret: 's3cret',
    })
    assert.equal(seen.request, 'POST /api/users/u2/tokens')
    assert.deepEqual(seen.body, { name: 'jenkins' })
  })

  it("maps error statuses to reasons and passes on the server's detail", async () => {
    const cases = [
      [400, 'invalid', "'password' must be at least 8 characters"],
      [403, 'forbidden', 'Access denied'],
      [404, 'not-found', 'User not found: u9'],
      [409, 'conflict', 'The last admin cannot be removed'],
    ] as const
    for (const [status, reason, detail] of cases) {
      answer(status, { status, detail })
      assert.deepEqual(await removeUser(base, 'u9', options), { ok: false, reason, detail })
    }
  })

  it('leaves detail out when the error body has none', async () => {
    answer(403)
    assert.deepEqual(await listUsers(base, options), { ok: false, reason: 'forbidden' })
  })

  it('reports unauthorized on a 401, so the session is dropped', async () => {
    answer(401, { status: 401, detail: 'Log in first' })
    assert.deepEqual(await listUsers(base, options), { ok: false, reason: 'unauthorized' })
  })

  it('reports bad-response for unexpected answers', async () => {
    const answers = [
      [200, [{ ...ayse, role: 'root' }]],
      [200, { users: [] }],
      [500, { status: 500 }],
    ] as const
    for (const [status, body] of answers) {
      answer(status, body)
      assert.deepEqual(await listUsers(base, options), { ok: false, reason: 'bad-response' })
    }
    answer(201, ci) // a token without its secret
    assert.deepEqual(await createToken(base, 'u2', 'jenkins', options), {
      ok: false,
      reason: 'bad-response',
    })
  })

  it('reports no-server without a saved server', async () => {
    assert.deepEqual(await listUsers(null, options), { ok: false, reason: 'no-server' })
  })
})
