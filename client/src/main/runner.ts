// Runs a test from the editor (#44): creates the run on the server, plays its steps one at a
// time against each step's own window, records every result in the outbox and tells the
// screen after each step. One run at a time per client. Free of Electron imports.

import type { RepoObjectSummary, RunsError, RunStatus } from '../shared/api.ts'
import type { ElementDescriptor } from '../shared/element.ts'
import { fromSummary, withOutcome, type LiveRun, type StepOutcome } from '../shared/liveRun.ts'
import type { Step } from '../shared/steps.ts'
import type { Outbox } from './outbox.ts'
import type { CreatedRun } from './runs.ts'
import { findWindow, systemClock, windowTitleOf, type Clock } from './runWindows.ts'
import { listWindows, type AgentCaller } from './spy.ts'
import { DEFAULT_STEP_TIMEOUT_MS, type StepPlayer } from './stepPlayer.ts'

export interface RunnerDeps {
  createRun(testId: string, appVersionId: string): Promise<{ ok: true; created: CreatedRun } | RunsError>
  /** The application's repository; null if it cannot be read. */
  repoObjects(): Promise<RepoObjectSummary[] | null>
  /** The object's element as last captured, for its window title. */
  capturedElement(objectId: string): Promise<Partial<ElementDescriptor> | undefined>
  agentConnected(): boolean
  agent: AgentCaller
  player: StepPlayer
  outbox: Pick<Outbox, 'add'>
  serverUrl: string
  clock?: Clock
}

export type StartAnswer =
  | { ok: true; runId: string }
  | { ok: false; reason: 'busy' | 'agent-not-connected' }
  | RunsError

/** The key the user's window choice is kept under for a target without a window title. */
const NO_TITLE = '\u0000'

type Window = { handle: number } | { stop: true } | { outcome: StepOutcome; agentGone: boolean }

export class Runner {
  private readonly deps: RunnerDeps
  private readonly clock: Clock
  private readonly listeners = new Set<(run: LiveRun) => void>()
  private run: LiveRun | null = null
  private stopping = false
  private answerChoice: ((handle: number | null) => void) | null = null

  constructor(deps: RunnerDeps) {
    this.deps = deps
    this.clock = deps.clock ?? systemClock
  }

  /** Creates the run; resolves once it exists on the server and plays it in the background. */
  async start(testId: string, appVersionId: string): Promise<StartAnswer> {
    if (this.run?.status === 'running') return { ok: false, reason: 'busy' }
    if (!this.deps.agentConnected()) return { ok: false, reason: 'agent-not-connected' }
    const answer = await this.deps.createRun(testId, appVersionId)
    if (!answer.ok) return answer
    this.stopping = false
    this.update(fromSummary(answer.created.run, true))
    void this.play(answer.created, appVersionId)
    return { ok: true, runId: answer.created.run.id }
  }

  /** Ends the run after the step being played; the steps after it are not run. */
  stop(): void {
    this.stopping = true
    this.choose(null)
  }

  /** Answers the window chooser: a window's handle, or null to stop. */
  choose(handle: number | null): void {
    const answer = this.answerChoice
    this.answerChoice = null
    answer?.(handle)
  }

  current(): LiveRun | null {
    return this.run
  }

  onChange(listener: (run: LiveRun) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** The outbox set the run aside: the server will not keep it. Playing goes on. */
  markNotStored(runId: string): void {
    if (this.run?.runId === runId) this.update({ ...this.run, problem: 'not-stored' })
  }

  private async play({ run, document }: CreatedRun, appVersionId: string): Promise<void> {
    const objects = new Map((await this.deps.repoObjects())?.map((object) => [object.name, object]))
    const chosen = new Map<string, number>()
    const steps = document.steps
    let status: RunStatus = 'passed'
    let next = 0
    for (; next < steps.length && !this.stopping; next++) {
      const step = steps[next]
      const timeoutMs = step.timeoutMs ?? DEFAULT_STEP_TIMEOUT_MS
      this.update({ ...this.run!, current: { stepIndex: next, startedAt: this.clock.now(), timeoutMs } })
      const outcomeOf = (message: string, category: string | null = null): StepOutcome => ({
        stepIndex: next,
        stepId: step.id ?? null,
        status: 'failed',
        durationMs: null,
        message,
        category,
      })
      const object = objects.get(step.target)
      let outcome: StepOutcome
      let agentGone = false
      if (!object) {
        outcome = outcomeOf(`the element "${step.target}" is not in the repository`)
      } else {
        const window = await this.windowFor(object, timeoutMs, chosen, outcomeOf)
        if ('stop' in window) break
        if ('outcome' in window) {
          ;({ outcome, agentGone } = window)
        } else {
          const played = await this.deps.player.play({
            step,
            stepIndex: next,
            stepId: step.id ?? null,
            version: document.version,
            handle: window.handle,
            target: { properties: object.primary, fallback: object.fallback },
            runId: run.id,
            appVersionId,
          })
          ;({ outcome, agentGone } = played)
        }
      }
      await this.record(run.id, outcome)
      if (agentGone) {
        status = 'aborted'
        next++
        break
      }
      if (outcome.status === 'failed') {
        status = 'failed'
        next++
        break
      }
    }
    if (this.stopping && status === 'passed') status = 'aborted'
    for (; next < steps.length; next++) {
      await this.record(run.id, notRun(next, steps[next]))
    }
    await this.deps.outbox.add({ kind: 'finish', serverUrl: this.deps.serverUrl, runId: run.id, status })
    this.update({ ...this.run!, status, current: null, choosing: null })
  }

  /** The handle to play a step on, the end of the run, or the step's failure. */
  private async windowFor(
    object: RepoObjectSummary,
    timeoutMs: number,
    chosen: Map<string, number>,
    outcomeOf: (message: string, category?: string | null) => StepOutcome,
  ): Promise<Window> {
    let title = windowTitleOf(object)
    if (title === null) title = windowTitleOf(object, await this.deps.capturedElement(object.id))
    const key = title ?? NO_TITLE
    const known = chosen.get(key)
    if (known !== undefined) return { handle: known }
    let candidates
    if (title === null) {
      const listed = await listWindows(this.deps.agent)
      if (!listed.ok) return gone(outcomeOf, listed.detail ?? 'the windows could not be listed', listed.reason)
      candidates = listed.windows
    } else {
      const found = await findWindow(this.deps.agent, title, timeoutMs, this.clock, () => this.stopping)
      if ('handle' in found) return found
      if ('failed' in found) return { outcome: outcomeOf(found.failed), agentGone: true }
      if ('none' in found) {
        if (this.stopping) return { stop: true }
        return {
          outcome: outcomeOf(`no window titled "${title}" appeared within ${timeoutMs} ms`, 'unexpectedWindow'),
          agentGone: false,
        }
      }
      candidates = found.many
    }
    this.update({ ...this.run!, choosing: { title, windows: candidates } })
    const handle = await new Promise<number | null>((resolve) => {
      this.answerChoice = resolve
    })
    this.update({ ...this.run!, choosing: null })
    if (handle === null) {
      this.stopping = true
      return { stop: true }
    }
    chosen.set(key, handle)
    return { handle }
  }

  private async record(runId: string, outcome: StepOutcome): Promise<void> {
    await this.deps.outbox.add({
      kind: 'result',
      serverUrl: this.deps.serverUrl,
      runId,
      stepIndex: outcome.stepIndex,
      body: resultBody(runId, outcome),
    })
    this.update(withOutcome(this.run!, outcome))
  }

  private update(run: LiveRun): void {
    this.run = run
    for (const listener of this.listeners) listener(run)
  }
}

function gone(
  outcomeOf: (message: string) => StepOutcome,
  message: string,
  reason: string,
): Window {
  return { outcome: outcomeOf(message), agentGone: reason === 'not-connected' }
}

function notRun(stepIndex: number, step: Step): StepOutcome {
  return { stepIndex, stepId: step.id ?? null, status: 'notRun', durationMs: null, message: null, category: null }
}

/** The `PUT` body: `run.stepResult`'s params, leaving out what is not known. */
function resultBody(runId: string, outcome: StepOutcome): Record<string, unknown> {
  const body: Record<string, unknown> = { runId, stepIndex: outcome.stepIndex }
  if (outcome.stepId !== null) body.stepId = outcome.stepId
  body.status = outcome.status
  if (outcome.durationMs !== null) body.durationMs = outcome.durationMs
  if (outcome.message !== null) body.message = outcome.message
  if (outcome.category !== null) body.category = outcome.category
  return body
}
