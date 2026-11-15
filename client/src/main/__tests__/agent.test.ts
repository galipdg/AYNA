import assert from 'node:assert/strict'
import { join } from 'node:path'
import { afterEach, describe, it } from 'node:test'
import type { AgentState, AgentStatus } from '../../shared/api.ts'
import {
  AgentManager,
  AgentNotConnectedError,
  AgentRpcError,
  AgentTimeoutError,
  describeExit,
  parseListening,
  resolveAgentCommand,
  type AgentManagerOptions,
} from '../agent.ts'

describe('resolveAgentCommand', () => {
  const args = ['-m', 'ayna_agent.rpc', '--port', '0']

  it('uses AYNA_AGENT_PYTHON when it is set', () => {
    const result = resolveAgentCommand({
      env: { AYNA_AGENT_PYTHON: 'C:\\AYNA\\python\\python.exe' },
      platform: 'win32',
      appPath: 'C:\\src\\AYNA\\client',
      exists: () => true,
    })
    assert.deepEqual(result, { command: 'C:\\AYNA\\python\\python.exe', args })
  })

  it("uses the agent's dev venv next to the client when it exists", () => {
    assert.equal(
      resolveAgentCommand({
        env: {},
        platform: 'win32',
        appPath: 'C:\\src\\AYNA\\client',
        exists: () => true,
      }).command,
      'C:\\src\\AYNA\\agent\\.venv\\Scripts\\python.exe',
    )
    assert.equal(
      resolveAgentCommand({
        env: {},
        platform: 'darwin',
        appPath: '/src/AYNA/client',
        exists: () => true,
      }).command,
      '/src/AYNA/agent/.venv/bin/python',
    )
  })

  it('falls back to Python from PATH', () => {
    const none = () => false
    assert.equal(
      resolveAgentCommand({ env: {}, platform: 'win32', appPath: 'C:\\x', exists: none }).command,
      'python',
    )
    assert.equal(
      resolveAgentCommand({ env: {}, platform: 'linux', appPath: '/x', exists: none }).command,
      'python3',
    )
  })
})

describe('describeExit', () => {
  const info = '2026-10-31 14:02:11,512 INFO websockets.server: connection open'

  it('names the signal on POSIX', () => {
    assert.equal(describeExit(null, 'SIGKILL', info), 'the agent was killed (SIGKILL)')
  })

  it('adds the last stderr line when it is an error', () => {
    const error = 'ModuleNotFoundError: No module named ayna_agent'
    assert.equal(describeExit(3, null, error), `the agent exited with code 3: ${error}`)
    const logged = '2026-10-31 14:02:11,512 ERROR ayna_agent.rpc: snapshot failed'
    assert.equal(describeExit(1, null, logged), `the agent exited with code 1: ${logged}`)
  })

  it('leaves out routine logging, as after a kill on Windows', () => {
    assert.equal(describeExit(1, null, info), 'the agent exited with code 1')
    assert.equal(describeExit(0, null, 'Traceback'), 'the agent exited with code 0')
  })

  it('shows large Windows exit codes in hex', () => {
    assert.equal(describeExit(4294967295, null, info), 'the agent exited with code 0xFFFFFFFF')
    assert.equal(describeExit(0xc000013a, null), 'the agent exited with code 0xC000013A')
  })
})

describe('parseListening', () => {
  it('reads the port from the listening line', () => {
    assert.equal(parseListening('{"event": "listening", "port": 53124}'), 53124)
  })

  it('rejects anything else', () => {
    for (const line of [
      '',
      'Hello',
      '{"event": "ready", "port": 1}',
      '{"event": "listening", "port": "80"}',
      '{"event": "listening", "port": 0}',
      '{"event": "listening", "port": 70000}',
      '{"event": "listening", "port": 1.5}',
    ]) {
      assert.equal(parseListening(line), null, line)
    }
  })
})

const fakeAgent = join(import.meta.dirname, 'fixtures', 'fake-agent.ts')

/** Runs the fake agent with Node itself, with timings short enough for tests. */
function manager(mode: string, overrides: Partial<AgentManagerOptions> = {}) {
  const agent = new AgentManager({
    command: {
      command: process.execPath,
      args: [
        '--experimental-strip-types',
        '--disable-warning=ExperimentalWarning',
        '--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',
        fakeAgent,
      ],
    },
    env: { ...process.env, FAKE_AGENT_MODE: mode },
    listenTimeoutMs: 5_000,
    heartbeatMs: 50,
    pingTimeoutMs: 200,
    restartDelayMs: 10,
    stopTimeoutMs: 300,
    log: () => {},
    ...overrides,
  })
  running.push(agent)
  return agent
}

const running: AgentManager[] = []
afterEach(async () => {
  await Promise.all(running.splice(0).map((agent) => agent.stop()))
})

/** Resolves with the status once `state` is reached, recording every state on the way. */
function waitFor(agent: AgentManager, state: AgentState, seen: AgentState[] = [], ms = 10_000) {
  return new Promise<AgentStatus>((resolve, reject) => {
    const timer = setTimeout(() => {
      unsubscribe()
      reject(new Error(`no ${state} within ${ms} ms; saw ${seen.join(' → ')}`))
    }, ms)
    const check = (status: AgentStatus) => {
      seen.push(status.state)
      if (status.state !== state) return
      clearTimeout(timer)
      unsubscribe()
      resolve(status)
    }
    const unsubscribe = agent.onStatus(check)
  })
}

function isRunning(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

describe('AgentManager', () => {
  it('starts the agent, connects with the token and answers calls', async () => {
    const agent = manager('ok')
    const seen: AgentState[] = []
    const connected = waitFor(agent, 'connected', seen)
    agent.start()
    assert.equal((await connected).restarts, 0)
    assert.deepEqual(seen, ['starting', 'connected'])
    assert.deepEqual(await agent.call('ping'), { agentVersion: '0.0.0', rpcVersion: '1.0' })
    await assert.rejects(agent.call('noSuchMethod'), (error: unknown) => {
      assert.ok(error instanceof AgentRpcError)
      assert.equal(error.code, -32601)
      assert.equal(error.rpcMessage, 'Method not found')
      assert.equal(error.message, 'Method not found (-32601)')
      return true
    })
  })

  it('refuses calls before it is connected and times out slow ones', async () => {
    const agent = manager('ok')
    await assert.rejects(agent.call('ping'), AgentNotConnectedError)
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    await assert.rejects(agent.call('block', { ms: 500 }, 50), AgentTimeoutError)
  })

  it('restarts the agent after it is killed', async () => {
    const agent = manager('ok')
    const first = waitFor(agent, 'connected')
    agent.start()
    await first
    const firstPid = agent.pid!
    const seen: AgentState[] = []
    const restarting = waitFor(agent, 'restarting')
    const again = waitFor(agent, 'connected', seen)
    process.kill(firstPid, 'SIGKILL')
    // Windows has no signals: Node's kill is TerminateProcess with exit code 1.
    const killed =
      process.platform === 'win32'
        ? 'the agent exited with code 1'
        : 'the agent was killed (SIGKILL)'
    assert.equal((await restarting).detail, killed)
    const status = await again
    assert.deepEqual(seen, ['restarting', 'connected'])
    assert.equal(status.restarts, 1)
    assert.notEqual(agent.pid, firstPid)
  })

  it('gives up after 3 restarts and reports why', async () => {
    const agent = manager('exit')
    const seen: AgentState[] = []
    const failed = waitFor(agent, 'failed', seen)
    agent.start()
    const status = await failed
    assert.deepEqual(seen, ['starting', 'restarting', 'restarting', 'restarting', 'failed'])
    assert.equal(status.restarts, 3)
    assert.match(status.detail!, /exited with code 3: ModuleNotFoundError/)
    assert.equal(agent.pid, undefined)
  })

  it('starts again with a fresh budget on retry', async () => {
    const agent = manager('exit', { maxRestarts: 0 })
    const failed = waitFor(agent, 'failed')
    agent.start()
    await failed
    const seen: AgentState[] = []
    const again = waitFor(agent, 'failed', seen)
    agent.retry()
    assert.equal((await again).restarts, 0)
    assert.deepEqual(seen, ['starting', 'failed'])
  })

  it('treats a missing or wrong port line as a failed start', async () => {
    const silent = manager('silent', { listenTimeoutMs: 200, maxRestarts: 0 })
    const garbage = manager('garbage', { maxRestarts: 0 })
    const silentFailed = waitFor(silent, 'failed')
    const garbageFailed = waitFor(garbage, 'failed')
    silent.start()
    garbage.start()
    assert.match((await silentFailed).detail!, /did not report its port within 200 ms/)
    assert.match((await garbageFailed).detail!, /unexpected first line from the agent: Hello/)
  })

  it('gives up on a WebSocket handshake that never completes', async () => {
    // The same timeout also covers the port line, so it must outlast a cold start of the
    // fake agent on a slow CI runner; 200 ms did not (PR #242).
    const agent = manager('no-handshake', { listenTimeoutMs: 2_000, maxRestarts: 0 })
    const failed = waitFor(agent, 'failed')
    agent.start()
    assert.match((await failed).detail!, /could not open a connection to the agent within 2000 ms/)
  })

  it('reports a command that cannot be started', async () => {
    const agent = new AgentManager({
      command: { command: 'ayna-no-such-python', args: [] },
      maxRestarts: 0,
      log: () => {},
    })
    running.push(agent)
    const failed = waitFor(agent, 'failed')
    agent.start()
    assert.match((await failed).detail!, /could not start ayna-no-such-python: .*ENOENT/)
  })

  it('restarts an agent that stops answering the heartbeat', async () => {
    const agent = manager('stop-answering')
    const seen: AgentState[] = []
    const restarting = waitFor(agent, 'restarting', seen)
    agent.start()
    assert.match((await restarting).detail!, /heartbeat failed: no answer to ping within 200 ms/)
    assert.deepEqual(seen, ['starting', 'connected', 'restarting'])
  })

  it('keeps the heartbeat going while a long call is running', async () => {
    const agent = manager('ok')
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    const seen: AgentState[] = []
    agent.onStatus((status) => seen.push(status.state))
    // Runs longer than pingTimeoutMs, as a long Wait step would; replies come in any order.
    const long = agent.call('block', { ms: 600 }, 2_000)
    await agent.call('ping', undefined, 100)
    await long
    assert.deepEqual(seen, [])
    assert.equal(agent.getStatus().state, 'connected')
  })

  it('stops the agent by closing its stdin', async () => {
    let killed = false
    const agent = manager('ok', { kill: () => (killed = true) })
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    const pid = agent.pid!
    await agent.stop()
    assert.equal(killed, false, 'exited on EOF, not by the kill timer')
    assert.equal(agent.getStatus().state, 'stopped')
    assert.equal(isRunning(pid), false)
  })

  it('lets the agent finish exiting while the heartbeat would fire', async () => {
    let killed = false
    const agent = manager('slow-exit', { stopTimeoutMs: 2_000, kill: () => (killed = true) })
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    await agent.stop()
    assert.equal(killed, false, 'heartbeatMs (50) < exit time (300) < stopTimeoutMs')
    assert.equal(agent.getStatus().state, 'stopped')
  })

  it('kills an agent that ignores stdin EOF', async () => {
    let killed = false
    const agent = manager('ignore-stdin', {
      kill: (child) => {
        killed = true
        child.kill('SIGKILL')
      },
    })
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    const pid = agent.pid!
    await agent.stop()
    assert.equal(killed, true)
    assert.equal(agent.getStatus().state, 'stopped')
    assert.equal(isRunning(pid), false)
  })

  it('settles stop() even when the kill does not take, so quitting cannot hang', async () => {
    const lines: string[] = []
    const agent = manager('ignore-stdin', {
      kill: () => {}, // taskkill denied, or a process stuck in the kernel (hasan, #154)
      killGraceMs: 200,
      log: (line) => lines.push(line),
    })
    const connected = waitFor(agent, 'connected')
    agent.start()
    await connected
    const pid = agent.pid!
    try {
      const started = Date.now()
      await agent.stop()
      assert.ok(Date.now() - started < 2_000, 'stopTimeoutMs (300) + killGraceMs (200)')
      assert.equal(agent.getStatus().state, 'stopped')
      assert.equal(agent.pid, undefined)
      assert.ok(lines.some((line) => line.includes(`could not stop the agent (pid ${pid})`)))
    } finally {
      process.kill(pid, 'SIGKILL')
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
    assert.equal(agent.getStatus().state, 'stopped', "the late 'exit' changes nothing")
  })

  it('does not restart while stopping, and stop is idempotent', async () => {
    const agent = manager('exit')
    const restarting = waitFor(agent, 'restarting')
    agent.start()
    await restarting
    await Promise.all([agent.stop(), agent.stop()])
    assert.equal(agent.getStatus().state, 'stopped')
    await new Promise((resolve) => setTimeout(resolve, 100))
    assert.equal(agent.pid, undefined)
  })
})
