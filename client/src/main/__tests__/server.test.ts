import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import { checkServer, normalizeServerUrl } from '../server.ts'

describe('normalizeServerUrl', () => {
  it('adds http:// when the scheme is missing', () => {
    assert.equal(normalizeServerUrl('ayna-server:8080'), 'http://ayna-server:8080')
    assert.equal(normalizeServerUrl('  10.0.0.5:8080  '), 'http://10.0.0.5:8080')
  })

  it('keeps http(s), lower-cases the host and drops trailing slashes', () => {
    assert.equal(normalizeServerUrl('HTTPS://Ayna.Local/'), 'https://ayna.local')
    assert.equal(normalizeServerUrl('http://host:8080/ayna//'), 'http://host:8080/ayna')
  })

  it('rejects empty input, other schemes, credentials, query and fragment', () => {
    for (const input of [
      '',
      '   ',
      'ftp://host',
      'file:///etc/passwd',
      'http://user:pass@host',
      'http://host/?x=1',
      'http://host/#top',
      'http://',
      'http://exa mple.com',
    ]) {
      assert.equal(normalizeServerUrl(input), null, input)
    }
  })
})

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('checkServer', () => {
  let server: Server
  let base: string
  let handle: (path: string, res: import('node:http').ServerResponse) => void

  before(async () => {
    server = createServer((req, res) => handle(req.url ?? '', res))
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`
  })

  after(() => {
    server.closeAllConnections()
    server.close()
  })

  function json(res: import('node:http').ServerResponse, status: number, body: unknown) {
    res.writeHead(status, { 'content-type': 'application/json' }).end(JSON.stringify(body))
  }

  it('connects when the health endpoint reports UP', async () => {
    let path = ''
    handle = (p, res) => {
      path = p
      json(res, 200, { status: 'UP', db: 'UP' })
    }
    assert.deepEqual(await checkServer(`${base}/`), { ok: true, url: base })
    assert.equal(path, '/api/health')
  })

  it('reports db-down when the server cannot reach Neo4j', async () => {
    handle = (_p, res) => json(res, 503, { status: 'DOWN', db: 'DOWN' })
    assert.deepEqual(await checkServer(base), { ok: false, reason: 'db-down', url: base })
  })

  it('reports not-ayna for other answers', async () => {
    const answers: Array<(res: import('node:http').ServerResponse) => void> = [
      (res) => json(res, 404, { error: 'Not Found' }),
      (res) => res.writeHead(200, { 'content-type': 'text/html' }).end('<html></html>'),
      (res) => json(res, 200, { hello: 'world' }),
      (res) => json(res, 503, { status: 'DOWN' }),
    ]
    for (const answer of answers) {
      handle = (_p, res) => answer(res)
      assert.deepEqual(await checkServer(base), { ok: false, reason: 'not-ayna', url: base })
    }
  })

  it('reports timeout when the server does not answer in time', async () => {
    handle = () => {} // never responds
    assert.deepEqual(await checkServer(base, { timeoutMs: 100 }), {
      ok: false,
      reason: 'timeout',
      url: base,
    })
  })

  it('reports unreachable when nothing listens', async () => {
    const closed = createServer()
    await new Promise<void>((resolve) => closed.listen(0, '127.0.0.1', resolve))
    const url = `http://127.0.0.1:${(closed.address() as AddressInfo).port}`
    await new Promise((resolve) => closed.close(resolve))
    assert.deepEqual(await checkServer(url), { ok: false, reason: 'unreachable', url })
  })

  it('reports invalid-url without sending a request', async () => {
    let called = false
    const fetch = (async () => {
      called = true
      throw new Error('should not be called')
    }) as typeof globalThis.fetch
    assert.deepEqual(await checkServer('ftp://host', { fetch }), {
      ok: false,
      reason: 'invalid-url',
    })
    assert.equal(called, false)
  })
})
