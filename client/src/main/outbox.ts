// The run outbox (#44, ADR runs-api-and-live-updates): every step result and every finish is
// written to disk first and then sent to the server in order, so a run's record survives a
// server that is away, an expired session and a client restart. Free of Electron imports.

import { readFile, rename, writeFile } from 'node:fs/promises'
import type { RunStatus } from '../shared/api.ts'
import type { WriteAnswer } from './runs.ts'
import { systemClock, type Clock } from './runWindows.ts'

export type OutboxEntry =
  | { kind: 'result'; serverUrl: string; runId: string; stepIndex: number; body: Record<string, unknown> }
  | { kind: 'finish'; serverUrl: string; runId: string; status: RunStatus }

export type SetAsideEntry = OutboxEntry & { answer: 'gone' | 'conflict' }

export interface OutboxFile {
  entries: OutboxEntry[]
  /** Entries the server will never take; kept so nothing is lost without a trace. */
  setAside: SetAsideEntry[]
  /**
   * Runs started on this machine whose finish is not queued yet. Results leave the file as
   * soon as they are delivered, so this is how a run cut short by a crash is still known.
   */
  open: { serverUrl: string; runId: string }[]
}

/** Sends one entry to the server it belongs to; `serverUrl` is the server signed in to now. */
export interface OutboxSender {
  serverUrl(): string | null
  put(entry: OutboxEntry): Promise<WriteAnswer>
}

export const FIRST_RETRY_MS = 1_000
export const LAST_RETRY_MS = 30_000

export class Outbox {
  private closed = false
  private paused = false
  private sending = false
  private retryMs = 0
  private saving: Promise<void> = Promise.resolve()
  private readonly idleWaiters: (() => void)[] = []
  private readonly setAsideListeners = new Set<(runId: string) => void>()

  private readonly file: string
  private readonly state: OutboxFile
  private readonly sender: OutboxSender
  private readonly clock: Clock
  private readonly log: (line: string) => void

  private constructor(
    file: string,
    state: OutboxFile,
    sender: OutboxSender,
    clock: Clock,
    log: (line: string) => void,
  ) {
    this.file = file
    this.state = state
    this.sender = sender
    this.clock = clock
    this.log = log
  }

  /** Reads the file (a missing one is empty, an unreadable one is kept as `.bad`) and starts sending. */
  static async open(
    file: string,
    sender: OutboxSender,
    clock: Clock = systemClock,
    log: (line: string) => void = console.log,
  ): Promise<Outbox> {
    let state: OutboxFile = { entries: [], setAside: [], open: [] }
    let text: string | null = null
    try {
      text = await readFile(file, 'utf8')
    } catch {
      // No outbox yet.
    }
    if (text !== null) {
      const read = parseFile(text)
      if (read) {
        state = read
      } else {
        log(`[outbox] ${file} could not be read; kept as ${file}.bad, starting empty`)
        await rename(file, `${file}.bad`)
      }
    }
    const outbox = new Outbox(file, state, sender, clock, log)
    void outbox.send()
    return outbox
  }

  /** Marks a run as started here; it is on disk when this resolves. Its finish clears it. */
  async opened(serverUrl: string, runId: string): Promise<void> {
    this.state.open.push({ serverUrl, runId })
    await this.save()
  }

  /** Queues an entry; it is on disk when this resolves. */
  async add(entry: OutboxEntry): Promise<void> {
    if (entry.kind === 'finish') {
      this.state.open = this.state.open.filter((run) => run.runId !== entry.runId)
    }
    if (this.isSetAside(entry.runId)) {
      this.state.setAside.push({ ...entry, answer: this.setAsideAnswer(entry.runId) })
    } else {
      this.state.entries.push(entry)
    }
    await this.save()
    void this.send()
  }

  /** Tries again now: after a sign-in, or when the server changed. */
  resume(): void {
    this.paused = false
    void this.send()
  }

  /** Runs on `serverUrl` started here whose finish was never queued. */
  unfinishedRuns(serverUrl: string): string[] {
    return this.state.open.filter((run) => run.serverUrl === serverUrl).map((run) => run.runId)
  }

  onSetAside(listener: (runId: string) => void): () => void {
    this.setAsideListeners.add(listener)
    return () => this.setAsideListeners.delete(listener)
  }

  /** Resolves when nothing is being sent: the queue is empty, or waiting for a sign-in. */
  idle(): Promise<void> {
    return this.sending ? new Promise((resolve) => this.idleWaiters.push(resolve)) : Promise.resolve()
  }

  /** Stops sending; what is queued stays on disk for the next start. */
  async close(): Promise<void> {
    this.closed = true
    await this.saving
  }

  private async send(): Promise<void> {
    if (this.sending || this.closed) return
    this.sending = true
    try {
      while (!this.closed && !this.paused) {
        const server = this.sender.serverUrl()
        const entry = this.state.entries.find((candidate) => candidate.serverUrl === server)
        if (!entry) break
        const answer = await this.sender.put(entry)
        if (this.closed) return
        if (answer === 'stored') {
          this.retryMs = 0
          this.remove(entry)
          await this.save()
        } else if (answer === 'retry') {
          this.retryMs = Math.min(this.retryMs ? this.retryMs * 2 : FIRST_RETRY_MS, LAST_RETRY_MS)
          await this.clock.sleep(this.retryMs)
        } else if (answer === 'unauthorized') {
          this.paused = true
        } else {
          this.setRunAside(entry.runId, answer)
          await this.save()
        }
      }
    } finally {
      this.sending = false
      for (const resolve of this.idleWaiters.splice(0)) resolve()
    }
  }

  private setRunAside(runId: string, answer: 'gone' | 'conflict'): void {
    const [moved, kept] = partition(this.state.entries, (entry) => entry.runId === runId)
    this.state.entries = kept
    this.state.setAside.push(...moved.map((entry) => ({ ...entry, answer })))
    this.log(`[outbox] the server refused run ${runId} (${answer}); its results were set aside`)
    for (const listener of this.setAsideListeners) listener(runId)
  }

  private isSetAside(runId: string): boolean {
    return this.state.setAside.some((entry) => entry.runId === runId)
  }

  private setAsideAnswer(runId: string): 'gone' | 'conflict' {
    return this.state.setAside.find((entry) => entry.runId === runId)!.answer
  }

  private remove(entry: OutboxEntry): void {
    this.state.entries = this.state.entries.filter((candidate) => candidate !== entry)
  }

  /** Writes the whole file, temp file + rename, one write at a time. */
  private save(): Promise<void> {
    const text = `${JSON.stringify(this.state)}\n`
    const write = async () => {
      const temp = `${this.file}.tmp`
      await writeFile(temp, text, 'utf8')
      await rename(temp, this.file)
    }
    this.saving = this.saving.then(write, write)
    return this.saving
  }
}

function partition<T>(items: T[], test: (item: T) => boolean): [T[], T[]] {
  return [items.filter(test), items.filter((item) => !test(item))]
}

function parseFile(text: string): OutboxFile | null {
  try {
    const value = JSON.parse(text) as Partial<OutboxFile>
    if (Array.isArray(value.entries) && Array.isArray(value.setAside)) {
      // A file from before runs were marked open has no `open`.
      const open = Array.isArray(value.open) ? value.open : []
      return { entries: value.entries, setAside: value.setAside, open }
    }
  } catch {
    // Unreadable.
  }
  return null
}
