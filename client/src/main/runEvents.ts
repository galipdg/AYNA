// Live runs of the test open in the editor (#44, FR-20, SC-17), from the server's `/ws/runs`.
// One connection, one watched test at a time. There is no replay on the server, so after
// every (re)subscription the running runs are read over REST and merged by `stepIndex`.
// Free of Electron imports: `index.ts` passes in Node's WebSocket.

import type { RunsResult, RunSummary } from '../shared/api.ts'
import { fromSummary, stepOutcomeFrom, withOutcome, withSummary, type LiveRun } from '../shared/liveRun.ts'
import type { getRun } from './runs.ts'
import { toRun } from './runs.ts'
import { FIRST_RETRY_MS, LAST_RETRY_MS } from './outbox.ts'
import { systemClock, type Clock } from './runWindows.ts'

/** The part of a WebSocket this module uses; Node's own WebSocket has it. */
export interface WebSocketLike {
  send(data: string): void
  close(code?: number): void
  addEventListener(type: 'message', listener: (event: { data: unknown }) => void): void
  addEventListener(type: 'close', listener: (event: { code?: number }) => void): void
  addEventListener(type: 'open' | 'error', listener: () => void): void
}

export interface RunEventsDeps {
  connect(url: string, token: string): WebSocketLike
  catchUp: {
    running(testId: string): Promise<RunsResult>
    get(runId: string): ReturnType<typeof getRun>
  }
  clock?: Clock
}

/** The server closes with this when the token has expired or was revoked. */
const POLICY_VIOLATION = 1008

export class RunEvents {
  private readonly deps: RunEventsDeps
  private readonly clock: Clock
  private readonly listeners = new Set<(run: LiveRun) => void>()
  private server: { url: string; token: string } | null = null
  private socket: WebSocketLike | null = null
  private open = false
  private watched: string | null = null
  private runs = new Map<string, LiveRun>()
  private retryMs = 0

  constructor(deps: RunEventsDeps) {
    this.deps = deps
    this.clock = deps.clock ?? systemClock
  }

  /** Connects to `serverUrl` with `token`, or closes without either. */
  setServer(serverUrl: string | null, token: string | null): void {
    this.disconnect()
    this.server = serverUrl && token ? { url: serverUrl, token } : null
    this.retryMs = 0
    if (this.server) this.connect()
  }

  /** Follows `testId`'s runs instead of the previous test's; null follows none. */
  watch(testId: string | null): void {
    if (testId === this.watched) return
    if (this.open && this.watched) this.sendMessage({ type: 'unsubscribe', testId: this.watched })
    this.watched = testId
    this.runs = new Map()
    if (this.open && testId) this.sendMessage({ type: 'subscribe', testId })
  }

  onRun(listener: (run: LiveRun) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private connect(): void {
    const server = this.server!
    const url = `${server.url.replace(/^http/, 'ws')}/ws/runs`
    const socket = this.deps.connect(url, server.token)
    this.socket = socket
    socket.addEventListener('open', () => {
      if (this.socket !== socket) return
      this.open = true
      this.retryMs = 0
      if (this.watched) this.sendMessage({ type: 'subscribe', testId: this.watched })
    })
    socket.addEventListener('message', (event: { data: unknown }) => {
      if (this.socket === socket) this.receive(event.data)
    })
    socket.addEventListener('close', (event: { code?: number }) => {
      if (this.socket !== socket) return
      this.socket = null
      this.open = false
      if (event.code === POLICY_VIOLATION) return // a new token comes with the next sign-in
      void this.reconnect(server)
    })
    socket.addEventListener('error', () => {
      // A close follows.
    })
  }

  private async reconnect(server: { url: string; token: string }): Promise<void> {
    this.retryMs = Math.min(this.retryMs ? this.retryMs * 2 : FIRST_RETRY_MS, LAST_RETRY_MS)
    await this.clock.sleep(this.retryMs)
    if (this.server === server && !this.socket) this.connect()
  }

  private disconnect(): void {
    const socket = this.socket
    this.socket = null
    this.open = false
    socket?.close()
  }

  private sendMessage(message: Record<string, unknown>): void {
    this.socket?.send(JSON.stringify(message))
  }

  private receive(data: unknown): void {
    let message: Record<string, unknown>
    try {
      message = JSON.parse(String(data)) as Record<string, unknown>
    } catch {
      return
    }
    const testId = this.watched
    if (!testId || message.testId !== testId) return
    if (message.type === 'subscribed') {
      void this.catchUp(testId)
    } else if (message.type === 'run.started' || message.type === 'run.finished') {
      const run = toRun(message.run)
      if (run) this.merge(run)
    } else if (message.type === 'run.stepResult') {
      const outcome = stepOutcomeFrom(message)
      const known = this.runs.get(String(message.runId))
      if (outcome && known) this.emit(withOutcome(known, outcome))
      else if (outcome) void this.fetchRun(testId, String(message.runId))
    }
  }

  private async catchUp(testId: string): Promise<void> {
    const running = await this.deps.catchUp.running(testId)
    if (!running.ok || this.watched !== testId) return
    for (const run of running.runs) await this.fetchRun(testId, run.id)
  }

  private async fetchRun(testId: string, runId: string): Promise<void> {
    const answer = await this.deps.catchUp.get(runId)
    if (!answer.ok || this.watched !== testId) return
    let run = this.merge(answer.run)
    for (const outcome of answer.outcomes) run = withOutcome(run, outcome)
    this.emit(run)
  }

  private merge(summary: RunSummary): LiveRun {
    const known = this.runs.get(summary.id)
    const run = known ? withSummary(known, summary) : fromSummary(summary, false)
    this.emit(run)
    return run
  }

  private emit(run: LiveRun): void {
    this.runs.set(run.runId, run)
    for (const listener of this.listeners) listener(run)
  }
}
