import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { RepoObjectSummary, RunsError, RunSummary } from '../../shared/api.ts'
import type { LiveRun, StepOutcome } from '../../shared/liveRun.ts'
import type { Step } from '../../shared/steps.ts'
import type { OutboxEntry } from '../outbox.ts'
import { Runner, type RunnerDeps } from '../runner.ts'
import type { Clock } from '../runWindows.ts'
import type { PlayRequest, PlayedStep } from '../stepPlayer.ts'

const LOGIN = 'AYNA Trial - Login'

const summary: RunSummary = {
  id: 'r1',
  testId: 't1',
  appVersionId: 'v1',
  status: 'running',
  stepCount: 3,
  startedBy: 'omer',
  startedAt: '2026-11-15T10:00:00Z',
  finishedAt: null,
  durationMs: null,
}

const object = (name: string, windowTitle?: string): RepoObjectSummary => ({
  id: `id-${name}`,
  name,
  primary: { automationId: name, ...(windowTitle === undefined ? {} : { windowTitle }) },
  fallback: {},
  columns: [],
  testCount: 1,
  versionIds: ['v1'],
})

const win = (handle: number, title: string) => ({
  handle,
  title,
  className: 'QWidget',
  processId: 1,
  processName: 'trial.exe',
  bounds: [0, 0, 100, 100],
})

const steps: Step[] = [
  { id: 's1', keyword: 'Type', target: 'login.userInput', value: 'admin' },
  { id: 's2', keyword: 'Type', target: 'login.passwordInput', value: 'admin' },
  { id: 's3', keyword: 'Click', target: 'login.okButton' },
]

const passed = (request: PlayRequest): PlayedStep => ({
  outcome: {
    stepIndex: request.stepIndex,
    stepId: request.stepId,
    status: 'passed',
    durationMs: 30,
    message: null,
    category: null,
  },
  agentGone: false,
})

const failed = (request: PlayRequest, agentGone = false): PlayedStep => ({
  outcome: { ...passed(request).outcome, status: 'failed', message: 'not there' },
  agentGone,
})

interface Setup {
  play?: (request: PlayRequest) => Promise<PlayedStep> | PlayedStep
  windows?: ReturnType<typeof win>[] | (() => ReturnType<typeof win>[])
  objects?: RepoObjectSummary[]
  createRun?: RunnerDeps['createRun']
  agentConnected?: boolean
}

function setup(options: Setup = {}) {
  const played: PlayRequest[] = []
  const outbox: OutboxEntry[] = []
  const states: LiveRun[] = []
  let now = 0
  const clock: Clock = {
    now: () => now,
    sleep: async (ms) => {
      now += ms
    },
  }
  const windows = options.windows ?? [win(7, LOGIN)]
  const deps: RunnerDeps = {
    createRun:
      options.createRun ??
      (async () => ({ ok: true, created: { run: summary, document: { version: '0.2', steps } } })),
    repoObjects: async () =>
      options.objects ?? [
        object('login.userInput', LOGIN),
        object('login.passwordInput', LOGIN),
        object('login.okButton', LOGIN),
      ],
    capturedElement: async () => undefined,
    agentConnected: () => options.agentConnected ?? true,
    agent: {
      async call(method: string) {
        assert.equal(method, 'listWindows')
        return { windows: typeof windows === 'function' ? windows() : windows }
      },
    },
    player: {
      async play(request) {
        played.push(request)
        return (options.play ?? passed)(request)
      },
    },
    outbox: {
      async add(entry) {
        outbox.push(entry)
      },
    },
    serverUrl: 'http://server',
    clock,
  }
  const runner = new Runner(deps)
  runner.onChange((run) => states.push(run))
  /** Resolves with the run once it has finished. */
  const finished = () =>
    new Promise<LiveRun>((resolve) => {
      const check = (run: LiveRun | null) => {
        if (run && run.status !== 'running') resolve(run)
      }
      check(runner.current())
      runner.onChange(check)
    })
  const summaryOf = () =>
    outbox.map((entry) =>
      entry.kind === 'result' ? `${entry.stepIndex}:${String(entry.body.status)}` : `finish:${entry.status}`,
    )
  return { runner, played, outbox, states, finished, summaryOf }
}

/** Resolves once `test` holds for the runner's current run. */
function until(runner: Runner, test: (run: LiveRun) => boolean) {
  return new Promise<LiveRun>((resolve) => {
    const current = runner.current()
    if (current && test(current)) return resolve(current)
    const off = runner.onChange((run) => {
      if (test(run)) {
        off()
        resolve(run)
      }
    })
  })
}

describe('the runner', () => {
  it('plays every step and finishes passed', async () => {
    const { runner, played, finished, summaryOf, outbox } = setup()
    const started = await runner.start('t1', 'v1')
    assert.deepEqual(started, { ok: true, runId: 'r1' })
    const run = await finished()
    assert.equal(run.status, 'passed')
    assert.equal(run.outcomes.length, 3)
    assert.equal(run.current, null)
    assert.deepEqual(summaryOf(), ['0:passed', '1:passed', '2:passed', 'finish:passed'])
    assert.deepEqual(
      played.map((request) => [request.handle, request.stepIndex, request.stepId]),
      [
        [7, 0, 's1'],
        [7, 1, 's2'],
        [7, 2, 's3'],
      ],
    )
    assert.deepEqual(played[0].target, { properties: { automationId: 'login.userInput', windowTitle: LOGIN }, fallback: {} })
    const first = outbox[0]
    assert.ok(first.kind === 'result')
    assert.deepEqual(first.body, { runId: 'r1', stepIndex: 0, stepId: 's1', status: 'passed', durationMs: 30 })
  })

  it('marks the rest notRun after a failure', async () => {
    const { runner, finished, summaryOf } = setup({
      play: (request) => (request.stepIndex === 1 ? failed(request) : passed(request)),
    })
    await runner.start('t1', 'v1')
    assert.equal((await finished()).status, 'failed')
    assert.deepEqual(summaryOf(), ['0:passed', '1:failed', '2:notRun', 'finish:failed'])
  })

  it('stops between steps', async () => {
    let release = () => {}
    const { runner, played, finished, summaryOf } = setup({
      play: (request) =>
        new Promise<PlayedStep>((resolve) => {
          release = () => resolve(passed(request))
        }),
    })
    await runner.start('t1', 'v1')
    await until(runner, (run) => run.current?.stepIndex === 0)
    await new Promise((resolve) => setImmediate(resolve))
    runner.stop()
    release()
    assert.equal((await finished()).status, 'aborted')
    assert.equal(played.length, 1)
    assert.deepEqual(summaryOf(), ['0:passed', '1:notRun', '2:notRun', 'finish:aborted'])
  })

  it('asks when two windows match and remembers the choice', async () => {
    const { runner, played, finished } = setup({ windows: [win(41, LOGIN), win(42, LOGIN)] })
    await runner.start('t1', 'v1')
    const choosing = await until(runner, (run) => run.choosing !== null)
    assert.equal(choosing.choosing?.title, LOGIN)
    assert.equal(choosing.choosing?.windows.length, 2)
    runner.choose(42)
    const run = await finished()
    assert.equal(run.status, 'passed')
    assert.equal(run.choosing, null)
    assert.deepEqual(
      played.map((request) => request.handle),
      [42, 42, 42],
    )
  })

  it('stops when the chooser is answered with Stop', async () => {
    const { runner, played, finished, summaryOf } = setup({ windows: [win(41, LOGIN), win(42, LOGIN)] })
    await runner.start('t1', 'v1')
    await until(runner, (run) => run.choosing !== null)
    runner.choose(null)
    assert.equal((await finished()).status, 'aborted')
    assert.equal(played.length, 0)
    assert.deepEqual(summaryOf(), ['0:notRun', '1:notRun', '2:notRun', 'finish:aborted'])
  })

  it('asks for a window when the target has no title', async () => {
    const objects = [object('login.userInput'), object('login.passwordInput'), object('login.okButton')]
    const { runner, played, finished } = setup({ objects, windows: [win(7, LOGIN), win(9, 'Notepad')] })
    await runner.start('t1', 'v1')
    const choosing = await until(runner, (run) => run.choosing !== null)
    assert.equal(choosing.choosing?.title, null)
    assert.equal(choosing.choosing?.windows.length, 2)
    runner.choose(7)
    assert.equal((await finished()).status, 'passed')
    assert.deepEqual(
      played.map((request) => request.handle),
      [7, 7, 7],
    )
  })

  it('fails a step whose window never appears', async () => {
    const { runner, played, finished, outbox } = setup({ windows: [win(9, 'Notepad')] })
    await runner.start('t1', 'v1')
    const run = await finished()
    assert.equal(run.status, 'failed')
    assert.equal(played.length, 0)
    const first = run.outcomes[0] as StepOutcome
    assert.equal(first.status, 'failed')
    assert.equal(first.category, 'unexpectedWindow')
    assert.match(first.message ?? '', /AYNA Trial - Login/)
    const entry = outbox[0]
    assert.ok(entry.kind === 'result')
    assert.equal(entry.body.category, 'unexpectedWindow')
  })

  it('fails a step whose target is not in the repository', async () => {
    const objects = [object('login.userInput', LOGIN), object('login.okButton', LOGIN)]
    const { runner, played, finished, summaryOf } = setup({ objects })
    await runner.start('t1', 'v1')
    const run = await finished()
    assert.equal(run.status, 'failed')
    assert.equal(played.length, 1)
    assert.match(run.outcomes[1].message ?? '', /login\.passwordInput/)
    assert.deepEqual(summaryOf(), ['0:passed', '1:failed', '2:notRun', 'finish:failed'])
  })

  it('finishes aborted when the agent goes away', async () => {
    const { runner, played, finished, summaryOf } = setup({
      play: (request) => (request.stepIndex === 1 ? failed(request, true) : passed(request)),
    })
    await runner.start('t1', 'v1')
    assert.equal((await finished()).status, 'aborted')
    assert.equal(played.length, 2)
    assert.deepEqual(summaryOf(), ['0:passed', '1:failed', '2:notRun', 'finish:aborted'])
  })

  it('does not play when the run cannot be created', async () => {
    const refused: RunsError = { ok: false, reason: 'unreachable' }
    const { runner, played, outbox } = setup({ createRun: async () => refused })
    assert.deepEqual(await runner.start('t1', 'v1'), refused)
    assert.equal(runner.current(), null)
    assert.equal(played.length, 0)
    assert.equal(outbox.length, 0)
  })

  it('does not start without an agent', async () => {
    const { runner } = setup({ agentConnected: false })
    assert.deepEqual(await runner.start('t1', 'v1'), { ok: false, reason: 'agent-not-connected' })
  })

  it('refuses a second run', async () => {
    const { runner, finished } = setup({ play: () => new Promise<PlayedStep>(() => {}) })
    await runner.start('t1', 'v1')
    assert.deepEqual(await runner.start('t1', 'v1'), { ok: false, reason: 'busy' })
    void finished
  })

  it('reports a run the server no longer has', async () => {
    let release = () => {}
    const { runner, finished } = setup({
      play: (request) =>
        request.stepIndex === 0
          ? new Promise<PlayedStep>((resolve) => {
              release = () => resolve(passed(request))
            })
          : passed(request),
    })
    await runner.start('t1', 'v1')
    await until(runner, (run) => run.current?.stepIndex === 0)
    runner.markNotStored('r1')
    assert.equal(runner.current()?.problem, 'not-stored')
    release()
    const run = await finished()
    assert.equal(run.status, 'passed', 'play goes on')
    assert.equal(run.problem, 'not-stored')
  })
})
