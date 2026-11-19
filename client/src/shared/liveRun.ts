// A run as the editor shows it while it plays and after (#44): this client's own run from the
// runner, and anyone's run from `/ws/runs`, merged into one shape. Pure, so both the main
// process and the renderer can use it.

import type { RunsError, RunStatus, RunSummary, WindowInfo } from './api.ts'

export const STEP_STATUSES = ['passed', 'failed', 'notRun'] as const
export type StepStatus = (typeof STEP_STATUSES)[number]

/** One step's result, whether it came from the agent, the server or a live event. */
export interface StepOutcome {
  stepIndex: number
  stepId: string | null
  status: StepStatus
  durationMs: number | null
  message: string | null
  /** FR-35's failure category (#63), only on a failed step and only when known. */
  category: string | null
}

/** The run waits for the user: two windows have the step's title, or the target has none. */
export interface WindowChoice {
  title: string | null
  windows: WindowInfo[]
}

export interface LiveRun {
  runId: string
  testId: string
  status: RunStatus
  stepCount: number
  startedBy: string
  startedAt: string
  durationMs: number | null
  /** Started by this client: it shows Stop and the step timer. */
  mine: boolean
  /** Sorted by `stepIndex`, at most one per index. */
  outcomes: StepOutcome[]
  /** The step being played (this client's run only); `startedAt` is a clock reading in ms. */
  current: { stepIndex: number; startedAt: number; timeoutMs: number } | null
  choosing: WindowChoice | null
  /** The server refused the run's writes (the test was deleted, or a write conflicted). */
  problem: 'not-stored' | null
}

export function fromSummary(run: RunSummary, mine: boolean): LiveRun {
  return {
    runId: run.id,
    testId: run.testId,
    status: run.status,
    stepCount: run.stepCount,
    startedBy: run.startedBy,
    startedAt: run.startedAt,
    durationMs: run.durationMs,
    mine,
    outcomes: [],
    current: null,
    choosing: null,
    problem: null,
  }
}

/** Adds a step's result. A stored result never changes, so the first one for an index wins. */
export function withOutcome(run: LiveRun, outcome: StepOutcome): LiveRun {
  if (run.outcomes.some((known) => known.stepIndex === outcome.stepIndex)) return run
  const outcomes = [...run.outcomes, outcome].sort((a, b) => a.stepIndex - b.stepIndex)
  return { ...run, outcomes }
}

/** Takes the server's status and duration; a run that has finished never becomes `running` again. */
export function withSummary(run: LiveRun, summary: RunSummary): LiveRun {
  if (run.status !== 'running' && summary.status === 'running') return run
  return {
    ...run,
    status: summary.status,
    stepCount: summary.stepCount,
    durationMs: summary.durationMs,
  }
}

/** A step result from the agent, the REST API or a `run.stepResult` event; null if it is none. */
export function stepOutcomeFrom(value: unknown): StepOutcome | null {
  if (typeof value !== 'object' || value === null) return null
  const v = value as Record<string, unknown>
  if (!Number.isInteger(v.stepIndex) || (v.stepIndex as number) < 0) return null
  if (!STEP_STATUSES.includes(v.status as StepStatus)) return null
  return {
    stepIndex: v.stepIndex as number,
    stepId: typeof v.stepId === 'string' ? v.stepId : null,
    status: v.status as StepStatus,
    durationMs: typeof v.durationMs === 'number' ? v.durationMs : null,
    message: typeof v.message === 'string' ? v.message : null,
    category: typeof v.category === 'string' ? v.category : null,
  }
}

/** The answer to Run: the run exists and plays, or why it did not start. */
export type StartRunResult =
  | { ok: true; runId: string }
  | { ok: false; reason: 'busy' }
  | { ok: false; reason: 'agent-not-connected' }
  | RunsError

export interface RunBarState {
  kind: 'running' | 'choosing' | 'passed' | 'failed' | 'aborted'
  /** The step the bar talks about, counted from 1: being played, failed, or first not run. */
  stepNumber: number
  /** Since the run started; `now` and `startedAt` are wall-clock times. */
  elapsedMs: number
  failed?: StepOutcome
}

/** What the run bar above the steps says (wireframe 8). */
export function runBarState(run: LiveRun, now: number): RunBarState {
  const elapsedMs = Math.max(0, now - Date.parse(run.startedAt))
  if (run.status === 'running') {
    const stepIndex = run.current?.stepIndex ?? run.outcomes.length
    return { kind: run.choosing ? 'choosing' : 'running', stepNumber: stepIndex + 1, elapsedMs }
  }
  const failed = run.outcomes.find((outcome) => outcome.status === 'failed')
  if (run.status === 'failed' || (run.status === 'aborted' && failed)) {
    const kind = run.status
    return { kind, stepNumber: (failed?.stepIndex ?? 0) + 1, elapsedMs, ...(failed && { failed }) }
  }
  if (run.status === 'aborted') {
    const notRun = run.outcomes.find((outcome) => outcome.status === 'notRun')
    return {
      kind: 'aborted',
      stepNumber: (notRun?.stepIndex ?? run.outcomes.length) + 1,
      elapsedMs,
    }
  }
  return { kind: 'passed', stepNumber: run.stepCount, elapsedMs }
}

export interface RowState {
  kind: 'none' | 'pending' | 'playing' | 'passed' | 'failed' | 'skipped'
  outcome?: StepOutcome
  waitedMs?: number
  timeoutMs?: number
}

/** What a step's Result cell shows; `now` is a reading of the same clock as `current.startedAt`. */
export function rowState(run: LiveRun | null, stepIndex: number, now: number): RowState {
  if (!run) return { kind: 'none' }
  const outcome = run.outcomes.find((known) => known.stepIndex === stepIndex)
  if (outcome) {
    const kind = outcome.status === 'notRun' ? 'skipped' : outcome.status
    return { kind, outcome }
  }
  if (run.current?.stepIndex === stepIndex) {
    return {
      kind: 'playing',
      waitedMs: Math.max(0, now - run.current.startedAt),
      timeoutMs: run.current.timeoutMs,
    }
  }
  return { kind: 'pending' }
}

/**
 * The line under a step's row: the agent's message on a failed step, and on a passed one too
 * (a SelectRow that selected the row but could not make it current, or selects cells, #268).
 * A skipped step says so in its Result cell and gets no line.
 */
export function rowNote(state: RowState): { text: string; failed: boolean } | null {
  const text = state.outcome?.message
  if (!text || (state.kind !== 'failed' && state.kind !== 'passed')) return null
  return { text, failed: state.kind === 'failed' }
}

/**
 * Whether the editor's steps are read-only: only while this client plays them. Another
 * client's run is shown, but it must not lock the test here (a stale one could for an hour).
 */
export function locksEditor(run: LiveRun | null): boolean {
  return run !== null && run.mine && run.status === 'running'
}
