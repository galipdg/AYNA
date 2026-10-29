import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import { createApplication, listApplications } from '../apps.ts'

const notepad = { id: 'a1', name: 'Notepad', technology: 'Win32' }

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('applications API', () => {
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

  describe('listApplications', () => {
    it('returns the applications from GET /api/apps', async () => {
      let request = ''
      handle = (req, _body, res) => {
        request = `${req.method} ${req.url}`
        json(res, 200, [notepad])
      }
      assert.deepEqual(await listApplications(base), { ok: true, apps: [notepad] })
      assert.equal(request, 'GET /api/apps')
    })

    it('reports bad-response for anything but a list of applications', async () => {
      const answers: Array<(res: ServerResponse) => void> = [
        (res) => json(res, 200, { apps: [] }),
        (res) => json(res, 200, [{ id: 'a1', name: 'Notepad' }]),
        (res) => json(res, 500, { error: 'Internal Server Error' }),
        (res) => res.writeHead(200, { 'content-type': 'text/html' }).end('<html></html>'),
      ]
      for (const answer of answers) {
        handle = (_req, _body, res) => answer(res)
        assert.deepEqual(await listApplications(base), { ok: false, reason: 'bad-response' })
      }
    })

    it('reports timeout when the server does not answer in time', async () => {
      handle = () => {} // never responds
      assert.deepEqual(await listApplications(base, { timeoutMs: 100 }), {
        ok: false,
        reason: 'timeout',
      })
    })

    it('reports unreachable when nothing listens', async () => {
      const closed = createServer()
      await new Promise<void>((resolve) => closed.listen(0, '127.0.0.1', resolve))
      const url = `http://127.0.0.1:${(closed.address() as AddressInfo).port}`
      await new Promise((resolve) => closed.close(resolve))
      assert.deepEqual(await listApplications(url), { ok: false, reason: 'unreachable' })
    })

    it('reports no-server without sending a request', async () => {
      let called = false
      const fetch = (async () => {
        called = true
        throw new Error('should not be called')
      }) as typeof globalThis.fetch
      assert.deepEqual(await listApplications(null, { fetch }), { ok: false, reason: 'no-server' })
      assert.equal(called, false)
    })
  })

  describe('createApplication', () => {
    it('posts name and technology as JSON and returns the created application', async () => {
      let request = ''
      handle = (req, body, res) => {
        request = `${req.method} ${req.url} ${req.headers['content-type']} ${body}`
        json(res, 201, notepad)
      }
      assert.deepEqual(await createApplication(base, 'Notepad', 'Win32'), {
        ok: true,
        app: notepad,
      })
      assert.equal(
        request,
        'POST /api/apps application/json {"name":"Notepad","technology":"Win32"}',
      )
    })

    it('maps 409 to duplicate and 400 to invalid, whatever the body', async () => {
      handle = (_req, _body, res) => json(res, 409, { error: 'Conflict' })
      assert.deepEqual(await createApplication(base, 'Notepad', 'Win32'), {
        ok: false,
        reason: 'duplicate',
      })
      handle = (_req, _body, res) => res.writeHead(400).end()
      assert.deepEqual(await createApplication(base, ' ', 'Win32'), {
        ok: false,
        reason: 'invalid',
      })
    })

    it('reports bad-response for an unexpected answer', async () => {
      handle = (_req, _body, res) => json(res, 201, { id: 'a1' })
      assert.deepEqual(await createApplication(base, 'Notepad', 'Win32'), {
        ok: false,
        reason: 'bad-response',
      })
    })
  })
})
