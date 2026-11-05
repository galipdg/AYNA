import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import { login, logout } from '../auth.ts'

const admin = { id: 'u1', username: 'admin', role: 'admin', createdAt: '2026-10-31T10:00:00Z' }

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('auth API', () => {
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

  describe('login', () => {
    it('posts the credentials and returns the token and the user', async () => {
      let request = ''
      let sent: unknown
      let authorization: string | undefined
      handle = (req, body, res) => {
        request = `${req.method} ${req.url}`
        sent = JSON.parse(body)
        authorization = req.headers.authorization
        json(res, 200, { token: 't0k3n', expiresAt: '2026-10-31T22:00:00Z', user: admin })
      }
      assert.deepEqual(await login(base, 'admin', 'pw-12345678'), {
        ok: true,
        session: { token: 't0k3n', user: { id: 'u1', username: 'admin', role: 'admin' } },
      })
      assert.equal(request, 'POST /api/auth/login')
      assert.deepEqual(sent, { username: 'admin', password: 'pw-12345678' })
      assert.equal(authorization, undefined)
    })

    it('reports wrong-credentials on a 401', async () => {
      handle = (_req, _body, res) =>
        json(res, 401, { status: 401, detail: 'Wrong user name or password' })
      assert.deepEqual(await login(base, 'admin', 'wrong'), {
        ok: false,
        reason: 'wrong-credentials',
      })
    })

    it('reports bad-response for anything but a token and a known role', async () => {
      const answers = [
        { status: 200, body: { token: 't', user: { ...admin, role: 'root' } } },
        { status: 200, body: { user: admin } },
        { status: 500, body: { error: 'Internal Server Error' } },
      ]
      for (const answer of answers) {
        handle = (_req, _body, res) => json(res, answer.status, answer.body)
        assert.deepEqual(await login(base, 'admin', 'pw'), { ok: false, reason: 'bad-response' })
      }
    })

    it('reports no-server without a saved server', async () => {
      assert.deepEqual(await login(null, 'admin', 'pw'), { ok: false, reason: 'no-server' })
    })
  })

  describe('logout', () => {
    it('posts to the logout endpoint with the session token', async () => {
      let request = ''
      handle = (req, _body, res) => {
        request = `${req.method} ${req.url} ${req.headers.authorization}`
        res.writeHead(204).end()
      }
      await logout(base, 't0k3n')
      assert.equal(request, 'POST /api/auth/logout Bearer t0k3n')
    })
  })
})
