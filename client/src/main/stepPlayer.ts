// Plays one step of a run (#44). The runner sees only `StepPlayer`, so when the agent sends a
// `run.stepResult` per step itself, a player built on those replaces this one and nothing else.
// Free of Electron imports.

import { stepOutcomeFrom, type StepOutcome } from '../shared/liveRun.ts'
import type { PropertySet } from '../shared/repository.ts'
import type { Step } from '../shared/steps.ts'
import { AgentNotConnectedError, AgentRpcError } from './agent.ts'
import { describeFailure, SNAPSHOT_TIMEOUT, type AgentCaller } from './spy.ts'

/** What a step without `timeoutMs` waits, as the agent defaults it (RS NFR-05). */
export const DEFAULT_STEP_TIMEOUT_MS = 10_000

/** How much longer than the step's own time the client waits for the agent's answer. */
export const STEP_MARGIN_MS = 10_000

export interface PlayRequest {
  step: Step
  /** The step's position in the run's copy of the document. */
  stepIndex: number
  stepId: string | null
  version: string
  handle: number
  /** The step's repository object; never null here, the runner fails a missing one itself. */
  target: { properties: PropertySet; fallback?: PropertySet } | null
  runId: string
  appVersionId: string
}

/** `agentGone`: the agent stopped, so the run cannot go on. It never reaches the server. */
export interface PlayedStep {
  outcome: StepOutcome
  agentGone: boolean
}

export interface StepPlayer {
  play(request: PlayRequest): Promise<PlayedStep>
}

/** Sends each step as a one-step `runSteps` call. */
export function perStepPlayer(agent: AgentCaller): StepPlayer {
  return {
    async play(request) {
      const { step, stepIndex, stepId } = request
      const targets = request.target ? { [step.target]: request.target } : {}
      const params = {
        handle: request.handle,
        steps: { version: request.version, steps: [step] },
        targets,
        runId: request.runId,
        appVersionId: request.appVersionId,
      }
      const waitMs = (step.timeoutMs ?? DEFAULT_STEP_TIMEOUT_MS) + STEP_MARGIN_MS
      const failed = (message: string, category: string | null = null): StepOutcome => ({
        stepIndex,
        stepId,
        status: 'failed',
        durationMs: null,
        message,
        category,
      })
      let answer: unknown
      try {
        answer = await agent.call('runSteps', params, waitMs)
      } catch (error) {
        const gone = error instanceof AgentNotConnectedError
        const searchIncomplete = error instanceof AgentRpcError && error.code === SNAPSHOT_TIMEOUT
        const { detail } = describeFailure(error)
        const message = detail || (error instanceof Error ? error.message : String(error))
        return {
          outcome: failed(message, searchIncomplete ? 'searchIncomplete' : null),
          agentGone: gone,
        }
      }
      const results = (answer as { results?: unknown } | null)?.results
      const outcome = Array.isArray(results) ? stepOutcomeFrom(results[0]) : null
      if (!outcome) {
        return { outcome: failed('the agent answered something unexpected'), agentGone: false }
      }
      return { outcome: { ...outcome, stepIndex, stepId }, agentGone: false }
    },
  }
}
