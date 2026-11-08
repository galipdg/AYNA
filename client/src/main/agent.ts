// Runs the local automation agent (`python -m ayna_agent.rpc`) as a child process and
// keeps one JSON-RPC connection to it. Contract: `docs/agent-rpc.md` (#16).
// Kept free of Electron imports so plain `node --test` can drive it with a fake agent.

import { spawn, type ChildProcess } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { existsSync } from 'node:fs'
import { posix, win32 } from 'node:path'
import { createInterface } from 'node:readline'
import type { AgentState, AgentStatus } from '../shared/api.ts'

export interface AgentCommand {
  command: string
  args: string[]
}

const AGENT_ARGS = ['-m', 'ayna_agent.rpc', '--port', '0']

/**
 * Which Python runs the agent: `AYNA_AGENT_PYTHON` if set, else the agent's dev
 * virtual environment next to the client (`../agent/.venv`), else `python` / `python3`
 * from PATH. The installer (#84) will point `AYNA_AGENT_PYTHON` at the bundled one.
 */
export function resolveAgentCommand(options: {
  env: NodeJS.ProcessEnv
  platform: NodeJS.Platform
  /** The client folder in development (`app.getAppPath()`). */
  appPath: string
  exists?: (path: string) => boolean
}): AgentCommand {
  const { env, platform, appPath, exists = existsSync } = options
  if (env.AYNA_AGENT_PYTHON) return { command: env.AYNA_AGENT_PYTHON, args: AGENT_ARGS }
  const venv =
    platform === 'win32'
      ? win32.join(appPath, '..', 'agent', '.venv', 'Scripts', 'python.exe')
      : posix.join(appPath, '..', 'agent', '.venv', 'bin', 'python')
  if (exists(venv)) return { command: venv, args: AGENT_ARGS }
  return { command: platform === 'win32' ? 'python' : 'python3', args: AGENT_ARGS }
}

/** The port from the agent's one stdout line, `{"event": "listening", "port": n}`, or null. */
export function parseListening(line: string): number | null {
  try {
    const message = JSON.parse(line) as { event?: unknown; port?: unknown }
    const { event, port } = message
    if (event !== 'listening' || !Number.isInteger(port)) return null
    return (port as number) > 0 && (port as number) < 65536 ? (port as number) : null
  } catch {
    return null
  }
}

// A routine record in the agent's log format (`ayna_agent/rpc.py`: asctime, level, name).
const ROUTINE_LOG = /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} (DEBUG|INFO|WARNING) /

/**
 * Why the agent process ended, for the status bar. Windows has no signals: a killed
 * child reports `signal === null` and a non-zero code (1 for `taskkill /F`, 0xFFFFFFFF
 * for some `TerminateProcess` callers), so a non-zero code alone does not mean a crash.
 * The last stderr line is added only when it is not routine logging, e.g. a Python error.
 */
export function describeExit(
  code: number | null,
  signal: NodeJS.Signals | null,
  lastStderrLine?: string,
): string {
  if (signal) return `the agent was killed (${signal})`
  // Windows exit codes are unsigned 32-bit; large ones are NTSTATUS values, read in hex.
  const shown = code !== null && code > 0x7fffffff ? `0x${code.toString(16).toUpperCase()}` : code
  const exit = `the agent exited with code ${shown}`
  if (code === 0 || !lastStderrLine || ROUTINE_LOG.test(lastStderrLine)) return exit
  return `${exit}: ${lastStderrLine}`
}

/**
 * Kills the agent and everything it started. On Windows a venv's `python.exe` is a
 * launcher whose child is the real interpreter, so only `taskkill /T` stops both
 * (`docs/agent-rpc.md`, learnings 2026-10-25).
 */
export function killTree(child: ChildProcess): void {
  if (child.exitCode !== null || child.signalCode !== null) return
  if (process.platform === 'win32' && child.pid !== undefined) {
    // Full path: System32 is not on every PATH (Git Bash, some service accounts).
    const taskkill = win32.join(process.env.SystemRoot ?? 'C:\\Windows', 'System32', 'taskkill.exe')
    spawn(taskkill, ['/F', '/T', '/PID', String(child.pid)], {
      stdio: 'ignore',
      windowsHide: true,
    }).on('error', () => child.kill())
  } else {
    child.kill('SIGKILL')
  }
}

export interface AgentManagerOptions {
  command: AgentCommand
  /** Environment for the agent; the session token is added to it. Default `process.env`. */
  env?: NodeJS.ProcessEnv
  /** Automatic restarts after a crash before the agent counts as failed. */
  maxRestarts?: number
  /** How long the agent may take to print its port (Python start and imports), and then to accept the WebSocket. */
  listenTimeoutMs?: number
  /** Heartbeat period; the heartbeat is a JSON-RPC `ping`, answered at once even during a long call. */
  heartbeatMs?: number
  pingTimeoutMs?: number
  /** Delay before the first restart; doubled for each further one. */
  restartDelayMs?: number
  /** After this long connected, the restart count goes back to 0. */
  stableMs?: number
  /** On quit: how long the agent gets to exit after its stdin closes before it is killed. */
  stopTimeoutMs?: number
  /**
   * On quit: how long the kill gets to take effect. After that `stop()` resolves anyway
   * (a denied `taskkill` or a process stuck in the kernel), so the app can always quit.
   */
  killGraceMs?: number
  kill?: (child: ChildProcess) => void
  log?: (line: string) => void
}

interface Pending {
  resolve(result: unknown): void
  reject(error: Error): void
  timer: NodeJS.Timeout
}

/** One running agent at a time, restarted after a crash; see `AgentStatus` for the states. */
export class AgentManager {
  private readonly options: Required<Omit<AgentManagerOptions, 'env'>> & {
    env: NodeJS.ProcessEnv
  }
  private status: AgentStatus
  private readonly listeners = new Set<(status: AgentStatus) => void>()

  private generation = 0
  private child?: ChildProcess
  private socket?: WebSocket
  /** Timers that belong to the current launch; cleared when it ends. */
  private readonly launchTimers = new Set<NodeJS.Timeout>()
  private readonly pending = new Map<number, Pending>()
  private nextId = 1
  private restartTimer?: NodeJS.Timeout
  private stableTimer?: NodeJS.Timeout

  private stopRequested = false
  private stopped?: Promise<void>
  private resolveStopped?: () => void
  private stopDeadline?: NodeJS.Timeout

  constructor(options: AgentManagerOptions) {
    this.options = {
      env: process.env,
      maxRestarts: 3,
      listenTimeoutMs: 20_000,
      heartbeatMs: 5_000,
      pingTimeoutMs: 5_000,
      restartDelayMs: 500,
      stableMs: 60_000,
      stopTimeoutMs: 3_000,
      killGraceMs: 2_000,
      kill: killTree,
      log: (line) => console.log(line),
      ...options,
    }
    this.status = { state: 'stopped', restarts: 0, maxRestarts: this.options.maxRestarts }
  }

  getStatus(): AgentStatus {
    return this.status
  }

  /** Calls `listener` on every status change; returns a function that unsubscribes. */
  onStatus(listener: (status: AgentStatus) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** The agent's process id while it runs (for tests and logs). */
  get pid(): number | undefined {
    return this.child?.pid
  }

  start(): void {
    if (this.child || this.stopRequested || this.status.state !== 'stopped') return
    this.setStatus('starting', 0)
    this.launch()
  }

  /** After `failed`: start again with a fresh restart budget. */
  retry(): void {
    if (this.stopRequested || this.status.state !== 'failed') return
    this.setStatus('starting', 0)
    this.launch()
  }

  /**
   * Stops the agent for good: closes its stdin (the agent exits on EOF) and kills its
   * process tree if it is still running after `stopTimeoutMs`. Always settles: if the
   * agent outlives the kill by `killGraceMs`, it is left behind (logged) and the status
   * goes to `stopped`, because quitting waits for this promise.
   */
  stop(): Promise<void> {
    if (this.stopped) return this.stopped
    this.stopRequested = true
    clearTimeout(this.restartTimer)
    clearTimeout(this.stableTimer)
    const child = this.child
    if (!child) {
      this.setStatus('stopped', this.status.restarts)
      this.stopped = Promise.resolve()
      return this.stopped
    }
    this.stopped = new Promise((resolve) => (this.resolveStopped = resolve))
    this.closeSocket()
    child.stdin?.end()
    this.launchTimer(this.options.stopTimeoutMs, () => this.options.kill(child))
    this.stopDeadline = setTimeout(() => {
      this.options.log(`[agent] could not stop the agent (pid ${child.pid}); quitting without it`)
      this.generation++ // a late 'exit' from this child must not run afterExit again
      this.endLaunch()
      this.afterExit('could not stop the agent')
    }, this.options.stopTimeoutMs + this.options.killGraceMs)
    return this.stopped
  }

  /**
   * Sends one JSON-RPC request to the agent and resolves with its `result`. The caller
   * owns the timeout: give long calls (snapshot, a run) more than the agent's own budget,
   * because an answer that arrives after `timeoutMs` is dropped.
   */
  call(method: string, params?: Record<string, unknown>, timeoutMs = 30_000): Promise<unknown> {
    const socket = this.socket
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('the agent is not connected'))
    }
    const id = this.nextId++
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`no answer to ${method} within ${timeoutMs} ms`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      socket.send(JSON.stringify({ jsonrpc: '2.0', id, method, ...(params && { params }) }))
    })
  }

  private launch(): void {
    const generation = ++this.generation
    const { command, args } = this.options.command
    const token = randomBytes(32).toString('hex')
    // The token goes in the environment, never on the command line (other processes can read that).
    const child = spawn(command, args, {
      env: { ...this.options.env, AYNA_AGENT_TOKEN: token },
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    })
    this.child = child
    if (child.pid !== undefined) this.options.log(`[agent] started ${command} (pid ${child.pid})`)

    let finished = false
    let reason: string | undefined
    const stderrTail: string[] = []

    const finish = (why: string) => {
      if (finished) return
      finished = true
      this.endLaunch()
      if (generation === this.generation) this.afterExit(why)
    }
    const fail = (why: string) => {
      // While stopping, the agent gets its EOF grace period; stop() owns the kill.
      if (this.stopRequested) return
      reason ??= why
      if (child.pid === undefined) finish(reason)
      else this.options.kill(child)
    }

    child.on('error', (error) => {
      reason ??= `could not start ${command}: ${error.message}`
      // Without a pid the process never ran, so no 'exit' follows.
      if (child.pid === undefined) finish(reason)
    })
    child.on('exit', (code, signal) => {
      finish(reason ?? describeExit(code, signal, stderrTail.at(-1)))
    })
    // Swallow EPIPE when the agent dies while we close its stdin.
    child.stdin?.on('error', () => {})

    createInterface({ input: child.stderr! }).on('line', (line) => {
      stderrTail.push(line)
      if (stderrTail.length > 5) stderrTail.shift()
      this.options.log(`[agent] ${line}`)
    })

    const listenTimer = this.launchTimer(this.options.listenTimeoutMs, () =>
      fail(`the agent did not report its port within ${this.options.listenTimeoutMs} ms`),
    )
    let sawFirstLine = false
    createInterface({ input: child.stdout! }).on('line', (line) => {
      if (sawFirstLine) return this.options.log(`[agent stdout] ${line}`)
      sawFirstLine = true
      clearTimeout(listenTimer)
      const port = parseListening(line)
      if (port === null) return fail(`unexpected first line from the agent: ${line.slice(0, 200)}`)
      this.connect(generation, port, token, fail)
    })
  }

  private connect(generation: number, port: number, token: string, fail: (why: string) => void) {
    // Node's WebSocket (undici) takes handshake headers in its init object; browsers cannot.
    const init = { headers: { Authorization: `Bearer ${token}` } } as unknown as string[]
    const socket = new WebSocket(`ws://127.0.0.1:${port}`, init)
    this.socket = socket
    let opened = false
    // A port nobody accepts on can time out rather than refuse on Windows (learnings
    // 2026-11-01), so the handshake gets its own deadline instead of waiting for the OS.
    const ms = this.options.listenTimeoutMs
    const openTimer = this.launchTimer(ms, () =>
      fail(`could not open a connection to the agent within ${ms} ms`),
    )

    socket.onopen = () => {
      opened = true
      clearTimeout(openTimer)
      this.call('ping', undefined, this.options.pingTimeoutMs).then(
        () => generation === this.generation && !this.stopRequested && this.connected(fail),
        (error: Error) => fail(`the agent did not answer ping: ${error.message}`),
      )
    }
    socket.onmessage = (event) => this.reply(event.data)
    socket.onclose = () => {
      if (socket !== this.socket) return
      const why = opened
        ? 'the connection to the agent closed'
        : 'could not open a connection to the agent'
      // The process usually exits at the same moment; give its exit code a chance to be the reason.
      this.launchTimer(1_000, () => fail(why))
    }
  }

  private connected(fail: (why: string) => void) {
    this.setStatus('connected', this.status.restarts)
    clearTimeout(this.stableTimer)
    this.stableTimer = setTimeout(() => {
      if (this.status.state === 'connected') this.setStatus('connected', 0)
    }, this.options.stableMs)
    const beat = () => {
      // The agent answers requests concurrently and in any order (agent RPC 0.1), so a ping
      // is answered even while a long snapshot or Wait step runs.
      this.call('ping', undefined, this.options.pingTimeoutMs).catch((error: Error) =>
        fail(`heartbeat failed: ${error.message}`),
      )
      this.launchTimer(this.options.heartbeatMs, beat)
    }
    this.launchTimer(this.options.heartbeatMs, beat)
  }

  private reply(data: unknown) {
    let message: { id?: unknown; result?: unknown; error?: { code?: number; message?: string } }
    try {
      message = JSON.parse(String(data))
    } catch {
      return this.options.log(`[agent] unreadable reply: ${String(data).slice(0, 200)}`)
    }
    const pending = typeof message.id === 'number' ? this.pending.get(message.id) : undefined
    if (!pending) return
    this.pending.delete(message.id as number)
    clearTimeout(pending.timer)
    if (message.error) {
      pending.reject(new Error(`${message.error.message ?? 'error'} (${message.error.code})`))
    } else {
      pending.resolve(message.result)
    }
  }

  private afterExit(why: string) {
    this.child = undefined
    clearTimeout(this.stableTimer)
    if (this.stopRequested) {
      clearTimeout(this.stopDeadline)
      this.setStatus('stopped', this.status.restarts)
      this.resolveStopped?.()
      return
    }
    this.options.log(`[agent] stopped unexpectedly: ${why}`)
    if (this.status.restarts >= this.options.maxRestarts) {
      this.setStatus('failed', this.status.restarts, why)
      return
    }
    const restarts = this.status.restarts + 1
    this.setStatus('restarting', restarts, why)
    this.restartTimer = setTimeout(
      () => this.launch(),
      this.options.restartDelayMs * 2 ** (restarts - 1),
    )
  }

  /** Ends the current launch: its socket, timers and pending calls. */
  private endLaunch() {
    this.closeSocket()
    for (const timer of this.launchTimers) clearTimeout(timer)
    this.launchTimers.clear()
    for (const [id, pending] of this.pending) {
      clearTimeout(pending.timer)
      pending.reject(new Error('the agent stopped'))
      this.pending.delete(id)
    }
  }

  private closeSocket() {
    const socket = this.socket
    this.socket = undefined
    socket?.close()
  }

  private launchTimer(ms: number, callback: () => void): NodeJS.Timeout {
    const timer = setTimeout(() => {
      this.launchTimers.delete(timer)
      callback()
    }, ms)
    this.launchTimers.add(timer)
    return timer
  }

  private setStatus(state: AgentState, restarts: number, detail?: string) {
    this.status = {
      state,
      restarts,
      maxRestarts: this.options.maxRestarts,
      ...(detail && { detail }),
    }
    for (const listener of this.listeners) listener(this.status)
  }
}
