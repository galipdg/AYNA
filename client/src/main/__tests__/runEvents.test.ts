import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { RunsResult } from '../../shared/api.ts'
import type { LiveRun } from '../../shared/liveRun.ts'
import { RunEvents, type WebSocketLike } from '../runEvents.ts'
import type { Clock } from '../runWindows.ts'

/** A run as the server sends it, in REST and in events. */
const serverRun = (status = 'running') => ({
  id: 'r1',
  testId: 'a',
  appVersionId: 'v1',
  status,
  stepCount: 2,
  startedBy: { id: 'u2', username: 'ayse' },
  startedAt: '2026-11-15T10:00:00Z',
  finishedAt: status === 'running' ? null : '2026-11-15T10:00:02Z',
  durationMs: status === 'running' ? null : 2000,
})

class FakeSocket implements WebSocketLike {
  readonly sent: unknown[] = []
  closed = false
  private readonly listeners = new Map<string, ((event: never) => void)[]>()
  readonly url: string
  readonly token: string
  constructor(url: string, token: string) {
    this.url = url
    this.token = token
  }
  send(data: string) {
    this.sent.push(JSON.parse(data))
  }
  close() {
    this.closed = true
  }
  addEventListener(type: string, listener: (event: never) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener])
  }
  emit(type: string, event: unknown = {}) {
    for (const listener of this.listeners.get(type) ?? []) listener(event as never)
  }
  message(value: unknown) {
    this.emit('message', { data: JSON.stringify(value) })
  }
}

const tick = () => new Promise((resolve) => setImmediate(resolve))

function setup(running: RunsResult = { ok: true, runs: [] }, results: unknown[] = []) {
  const sockets: FakeSocket[] = []
  const slept: number[] = []
  const clock: Clock = { now: () => 0, sleep: async (ms) => void slept.push(ms) }
  let catchUps = 0
  const events = new RunEvents({
    connect: (url, token) => {
      const socket = new FakeSocket(url, token)
      sockets.push(socket)
      return socket
    },
    catchUp: {
      running: async () => {
        catchUps++
        return running
      },
      get: async () => ({
        ok: true,
        run: { ...serverRun(), startedBy: 'ayse', finishedAt: null, durationMs: null, status: 'running' as const },
        outcomes: results.map((r) => r as never),
      }),
    },
    clock,
  })
  const seen: LiveRun[] = []
  events.onRun((run) => seen.push(run))
  return { events, sockets, slept, seen, catchUps: () => catchUps }
}

describe('live runs from the server', () => {
  it('connects to /ws/runs with the token', () => {
    const { events, sockets } = setup()
    events.setServer('https://server:8443', 'tok')
    assert.equal(sockets[0].url, 'wss://server:8443/ws/runs')
    assert.equal(sockets[0].token, 'tok')
  })

  it('subscribes to the watched test and moves on', () => {
    const { events, sockets } = setup()
    events.setServer('http://server', 'tok')
    events.watch('a')
    sockets[0].emit('open')
    events.watch('b')
    assert.deepEqual(sockets[0].sent, [
      { type: 'subscribe', testId: 'a' },
      { type: 'unsubscribe', testId: 'a' },
      { type: 'subscribe', testId: 'b' },
    ])
  })

  it('catches up after subscribed', async () => {
    const results = [
      { stepIndex: 0, stepId: null, status: 'passed', durationMs: 3, message: null, category: null },
      { stepIndex: 1, stepId: null, status: 'failed', durationMs: 4, message: 'x', category: null },
    ]
    const running: RunsResult = {
      ok: true,
      runs: [{ ...serverRun(), startedBy: 'ayse', status: 'running', finishedAt: null, durationMs: null }],
    }
    const { events, sockets, seen } = setup(running, results)
    events.setServer('http://server', 'tok')
    events.watch('a')
    sockets[0].emit('open')
    sockets[0].message({ type: 'subscribed', testId: 'a' })
    await tick()
    const last = seen.at(-1)!
    assert.equal(last.runId, 'r1')
    assert.equal(last.mine, false)
    assert.equal(last.startedBy, 'ayse')
    assert.equal(last.outcomes.length, 2)
  })

  it('merges live events', () => {
    const { events, sockets, seen } = setup()
    events.setServer('http://server', 'tok')
    events.watch('a')
    sockets[0].emit('open')
    sockets[0].message({ type: 'run.started', testId: 'a', run: serverRun() })
    const step = { type: 'run.stepResult', testId: 'a', runId: 'r1', stepIndex: 0, stepId: null, status: 'passed' }
    sockets[0].message(step)
    sockets[0].message({ ...step, status: 'failed' })
    sockets[0].message({ type: 'run.started', testId: 'other', run: { ...serverRun(), id: 'r9', testId: 'other' } })
    sockets[0].message({ type: 'run.finished', testId: 'a', run: serverRun('failed') })
    const last = seen.at(-1)!
    assert.equal(last.runId, 'r1')
    assert.equal(last.status, 'failed')
    assert.deepEqual(
      last.outcomes.map((o) => o.status),
      ['passed'],
    )
    assert.ok(seen.every((run) => run.testId === 'a'))
  })

  it('reconnects and catches up again', async () => {
    const { events, sockets, slept, catchUps } = setup()
    events.setServer('http://server', 'tok')
    events.watch('a')
    sockets[0].emit('open')
    sockets[0].message({ type: 'subscribed', testId: 'a' })
    sockets[0].emit('close', { code: 1006 })
    await tick()
    assert.deepEqual(slept, [1000])
    assert.equal(sockets.length, 2)
    sockets[1].emit('open')
    assert.deepEqual(sockets[1].sent, [{ type: 'subscribe', testId: 'a' }])
    sockets[1].message({ type: 'subscribed', testId: 'a' })
    await tick()
    assert.equal(catchUps(), 2)
  })

  it('waits for a new token after 1008', async () => {
    const { events, sockets } = setup()
    events.setServer('http://server', 'tok')
    sockets[0].emit('open')
    sockets[0].emit('close', { code: 1008 })
    await tick()
    assert.equal(sockets.length, 1)
    events.setServer('http://server', 'new')
    assert.equal(sockets.length, 2)
    assert.equal(sockets[1].token, 'new')
  })

  it('closes without a server or token', () => {
    const { events, sockets } = setup()
    events.setServer('http://server', 'tok')
    events.setServer(null, null)
    assert.ok(sockets[0].closed)
    assert.equal(sockets.length, 1)
  })
})
