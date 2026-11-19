import assert from 'node:assert/strict'
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { after, before, describe, it } from 'node:test'
import { formatDuration, setStringsLanguage } from '../../renderer/src/strings.ts'
import {
  createRun,
  fetchReport,
  finishRun,
  getRun,
  listRunningRuns,
  listRuns,
  putResult,
  putScreenshot,
  reportFileName,
} from '../runs.ts'

/** A run as the server's `RunSummary` sends it (#44). */
const summary = {
  id: 'r1',
  testId: 't1',
  appVersionId: 'v1',
  status: 'failed',
  stepCount: 3,
  startedBy: { id: 'u1', username: 'ayse' },
  startedAt: '2026-11-10T12:00:00Z',
  finishedAt: '2026-11-10T12:00:03Z',
  durationMs: 3000,
}

const run = {
  id: 'r1',
  testId: 't1',
  appVersionId: 'v1',
  status: 'failed',
  stepCount: 3,
  startedBy: 'ayse',
  startedAt: '2026-11-10T12:00:00Z',
  finishedAt: '2026-11-10T12:00:03Z',
  durationMs: 3000,
}

/** A local HTTP server whose handler each test swaps in; requests never leave the machine. */
describe('runs API', () => {
  let server: Server
  let base: string
  let handle: (req: IncomingMessage, res: ServerResponse) => void

  before(async () => {
    server = createServer((req, res) => handle(req, res))
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

  it('lists the runs of one application with the filter as query and the token', async () => {
    let request = ''
    handle = (req, res) => {
      request = `${req.method} ${req.url} ${req.headers.authorization}`
      json(res, 200, [summary])
    }
    assert.deepEqual(
      await listRuns(base, 'a 1', { testId: 't 1', status: 'failed' }, { token: 't' }),
      { ok: true, runs: [run] },
    )
    assert.equal(request, 'GET /api/apps/a%201/runs?testId=t+1&status=failed Bearer t')

    await listRuns(base, 'a1', {})
    assert.equal(request, 'GET /api/apps/a1/runs undefined')
  })

  it('shows a running run without an end, and a removed account by its id', async () => {
    handle = (_req, res) =>
      json(res, 200, [
        {
          ...summary,
          status: 'running',
          finishedAt: null,
          durationMs: null,
          startedBy: { id: 'u9' },
        },
      ])
    assert.deepEqual(await listRuns(base, 'a1', {}), {
      ok: true,
      runs: [{ ...run, status: 'running', finishedAt: null, durationMs: null, startedBy: 'u9' }],
    })
  })

  it('maps 404 to not-found with the server message, and anything odd to bad-response', async () => {
    handle = (_req, res) => json(res, 404, { status: 404, detail: 'Application not found: a1' })
    assert.deepEqual(await listRuns(base, 'a1', {}), {
      ok: false,
      reason: 'not-found',
      detail: 'Application not found: a1',
    })
    handle = (_req, res) => json(res, 200, [{ ...summary, status: 'paused' }])
    assert.deepEqual(await listRuns(base, 'a1', {}), { ok: false, reason: 'bad-response' })
    handle = (_req, res) => json(res, 401, {})
    assert.deepEqual(await listRuns(base, 'a1', {}), { ok: false, reason: 'unauthorized' })
  })

  it('fetches the report as HTML in the asked language, with the token', async () => {
    let request = ''
    handle = (req, res) => {
      request = `${req.url} ${req.headers.authorization} ${req.headers.accept}`
      res.writeHead(200, { 'content-type': 'text/html;charset=UTF-8' }).end('<!DOCTYPE html>Ş')
    }
    assert.deepEqual(await fetchReport(base, 'r 1', 'tr', { token: 't' }), {
      ok: true,
      html: '<!DOCTYPE html>Ş',
    })
    assert.equal(request, '/api/runs/r%201/report.html?lang=tr Bearer t text/html')
  })

  it('reads a failed report request as a problem', async () => {
    handle = (_req, res) => json(res, 404, { status: 404, detail: 'Run not found: r1' })
    assert.deepEqual(await fetchReport(base, 'r1', 'en'), {
      ok: false,
      reason: 'not-found',
      detail: 'Run not found: r1',
    })
    handle = (_req, res) => json(res, 401, {})
    assert.deepEqual(await fetchReport(base, 'r1', 'en'), { ok: false, reason: 'unauthorized' })
    assert.deepEqual(await fetchReport(null, 'r1', 'en'), { ok: false, reason: 'no-server' })
  })

  it('says timeout when the report takes too long', async () => {
    handle = () => {}
    assert.deepEqual(await fetchReport(base, 'r1', 'en', { timeoutMs: 50 }), {
      ok: false,
      reason: 'timeout',
    })
  })
})

describe('reportFileName', () => {
  it('keeps a readable name and makes it safe on Windows', () => {
    assert.equal(reportFileName('AYNA Giriş 2026-11-10 15-04'), 'AYNA Giriş 2026-11-10 15-04.html')
    assert.equal(reportFileName('a/b\\c:d*e?f"g<h>i|j'), 'a-b-c-d-e-f-g-h-i-j.html')
    assert.equal(reportFileName('../..\u0001secret.html'), '-..-secret.html')
    assert.equal(reportFileName('  '), 'ayna-run.html')
    assert.equal(reportFileName('x'.repeat(300)).length, 125)
  })

  it('never gives one of the names Windows reserves for devices', () => {
    assert.equal(reportFileName('CON'), 'ayna-run CON.html')
    assert.equal(reportFileName('nul.txt'), 'ayna-run nul.txt.html')
    assert.equal(reportFileName('com1'), 'ayna-run com1.html')
    assert.equal(reportFileName('CONSOLE'), 'CONSOLE.html')
  })
})

describe('formatDuration', () => {
  it('picks the unit after rounding, so 59.96 s reads as a minute', () => {
    setStringsLanguage('tr')
    assert.equal(formatDuration(850), '850 ms')
    assert.equal(formatDuration(2500), '2,5 sn')
    assert.equal(formatDuration(59_940), '59,9 sn')
    assert.equal(formatDuration(59_960), '1 dk 0 sn')
    assert.equal(formatDuration(184_000), '3 dk 4 sn')
    setStringsLanguage('en')
    assert.equal(formatDuration(2500), '2.5 s')
  })
})

/** A `fetch` that answers `status` with `body` and records what was asked. */
function fakeFetch(status: number, body: unknown, seen: { url?: string; init?: RequestInit } = {}) {
  return (async (url: string, init?: RequestInit) => {
    seen.url = url
    seen.init = init
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    })
  }) as unknown as typeof globalThis.fetch
}

const throwing = (async () => {
  throw new TypeError('fetch failed')
}) as unknown as typeof globalThis.fetch

describe('a run from the editor (#44)', () => {
  const base = 'http://server'

  it('createRun posts the test and version and returns the copied document', async () => {
    const seen: { url?: string; init?: RequestInit } = {}
    const document = { version: '0.2', steps: [{ keyword: 'Click', target: 'login.okButton' }] }
    const answer = await createRun(base, 't1', 'v1', {
      fetch: fakeFetch(
        201,
        {
          ...summary,
          status: 'running',
          finishedAt: null,
          durationMs: null,
          document,
          results: [],
        },
        seen,
      ),
    })
    assert.equal(seen.url, `${base}/api/runs`)
    assert.equal(seen.init?.method, 'POST')
    assert.deepEqual(JSON.parse(String(seen.init?.body)), { testId: 't1', appVersionId: 'v1' })
    assert.ok(answer.ok)
    assert.equal(answer.created.document.steps.length, 1)
    assert.equal(answer.created.run.startedBy, 'ayse')
    const bad = await createRun(base, 't1', 'v1', { fetch: fakeFetch(400, { detail: 'no steps' }) })
    assert.deepEqual(bad, { ok: false, reason: 'invalid', detail: 'no steps' })
    const gone = await createRun(base, 't1', 'v1', { fetch: fakeFetch(404, {}) })
    assert.deepEqual(gone, { ok: false, reason: 'not-found' })
  })

  it('putResult maps statuses', async () => {
    const cases: [number, string][] = [
      [201, 'stored'],
      [200, 'stored'],
      [401, 'unauthorized'],
      [404, 'gone'],
      [409, 'conflict'],
      [400, 'conflict'],
      [503, 'retry'],
    ]
    for (const [status, expected] of cases) {
      const answer = await putResult(
        base,
        'r1',
        { stepIndex: 0, status: 'passed' },
        { fetch: fakeFetch(status, {}) },
      )
      assert.equal(answer, expected, `HTTP ${status}`)
    }
    assert.equal(await putResult(base, 'r1', { stepIndex: 0 }, { fetch: throwing }), 'retry')
    assert.equal(await putResult(null, 'r1', { stepIndex: 0 }, {}), 'retry')
    const seen: { url?: string; init?: RequestInit } = {}
    await putResult(
      base,
      'r/1',
      { runId: 'r/1', stepIndex: 3, status: 'passed' },
      { fetch: fakeFetch(201, {}, seen) },
    )
    assert.equal(seen.url, `${base}/api/runs/r%2F1/results/3`)
    assert.equal(seen.init?.method, 'PUT')
  })

  it('putScreenshot sends the PNG and maps statuses (#261)', async () => {
    const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47])
    const seen: { url?: string; init?: RequestInit } = {}
    assert.equal(
      await putScreenshot(base, 'r/1', 2, png, { fetch: fakeFetch(201, {}, seen) }),
      'stored',
    )
    assert.equal(seen.url, `${base}/api/runs/r%2F1/results/2/screenshot`)
    assert.equal(seen.init?.method, 'PUT')
    assert.equal((seen.init?.headers as Record<string, string>)['content-type'], 'image/png')
    assert.equal(seen.init?.body, png)
    const cases: [number, string][] = [
      [200, 'stored'],
      [404, 'gone'],
      [409, 'conflict'],
      [413, 'conflict'],
      [415, 'conflict'],
      [400, 'conflict'],
      [503, 'retry'],
      [401, 'unauthorized'],
    ]
    for (const [status, expected] of cases) {
      assert.equal(
        await putScreenshot(base, 'r1', 0, png, { fetch: fakeFetch(status, {}) }),
        expected,
        `HTTP ${status}`,
      )
    }
  })

  it('finishRun posts the status', async () => {
    const seen: { url?: string; init?: RequestInit } = {}
    assert.equal(
      await finishRun(base, 'r1', 'aborted', { fetch: fakeFetch(200, summary, seen) }),
      'stored',
    )
    assert.equal(seen.url, `${base}/api/runs/r1/finish`)
    assert.deepEqual(JSON.parse(String(seen.init?.body)), { status: 'aborted' })
    assert.equal(await finishRun(base, 'r1', 'passed', { fetch: fakeFetch(409, {}) }), 'conflict')
  })

  it('getRun reads results', async () => {
    const results = [
      {
        id: 'b',
        stepIndex: 1,
        stepId: null,
        status: 'failed',
        durationMs: 4,
        message: 'x',
        receivedAt: 'z',
      },
      {
        id: 'a',
        stepIndex: 0,
        stepId: 's1',
        status: 'passed',
        durationMs: 3,
        message: null,
        receivedAt: 'z',
      },
    ]
    const answer = await getRun(base, 'r1', {
      fetch: fakeFetch(200, { ...summary, document: {}, results }),
    })
    assert.ok(answer.ok)
    assert.deepEqual(
      answer.outcomes.map((o) => [o.stepIndex, o.status]),
      [
        [0, 'passed'],
        [1, 'failed'],
      ],
    )
  })

  it('listRunningRuns asks for the running runs of one test', async () => {
    const seen: { url?: string; init?: RequestInit } = {}
    const answer = await listRunningRuns(base, 't 1', { fetch: fakeFetch(200, [summary], seen) })
    assert.equal(seen.url, `${base}/api/tests/t%201/runs?status=running`)
    assert.ok(answer.ok)
    assert.equal(answer.runs.length, 1)
  })
})
