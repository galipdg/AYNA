import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { RunSummary } from '../../shared/api.ts'
import { fromSummary, stepOutcomeFrom, withOutcome, withSummary } from '../../shared/liveRun.ts'

const summary: RunSummary = {
  id: 'r1',
  testId: 't1',
  appVersionId: 'v1',
  status: 'running',
  stepCount: 3,
  startedBy: 'ayse',
  startedAt: '2026-11-15T10:00:00Z',
  finishedAt: null,
  durationMs: null,
}

const outcome = (stepIndex: number, status: 'passed' | 'failed' | 'notRun') => ({
  stepIndex,
  stepId: null,
  status,
  durationMs: null,
  message: null,
  category: null,
})

describe('live run', () => {
  it('withOutcome keeps the first result for an index', () => {
    let run = fromSummary(summary, true)
    run = withOutcome(run, outcome(1, 'passed'))
    run = withOutcome(run, outcome(1, 'failed'))
    assert.deepEqual(
      run.outcomes.map((o) => [o.stepIndex, o.status]),
      [[1, 'passed']],
    )
    run = withOutcome(withOutcome(run, outcome(2, 'passed')), outcome(0, 'passed'))
    assert.deepEqual(
      run.outcomes.map((o) => o.stepIndex),
      [0, 1, 2],
    )
  })

  it('withSummary never moves a finished run back to running', () => {
    const finished = withSummary(fromSummary(summary, false), {
      ...summary,
      status: 'failed',
      finishedAt: '2026-11-15T10:00:05Z',
      durationMs: 5000,
    })
    const again = withSummary(finished, summary)
    assert.equal(again.status, 'failed')
    assert.equal(again.durationMs, 5000)
  })

  it('stepOutcomeFrom reads all three shapes', () => {
    const agent = { stepIndex: 0, status: 'failed', durationMs: 12, message: 'no', category: 'timeout' }
    assert.deepEqual(stepOutcomeFrom(agent), {
      stepIndex: 0,
      stepId: null,
      status: 'failed',
      durationMs: 12,
      message: 'no',
      category: 'timeout',
    })
    const rest = {
      id: 'sr1',
      stepIndex: 2,
      stepId: 's3',
      status: 'passed',
      durationMs: 5,
      message: null,
      receivedAt: '2026-11-15T10:00:01Z',
      screenshotUrl: null,
    }
    assert.deepEqual(stepOutcomeFrom(rest), {
      stepIndex: 2,
      stepId: 's3',
      status: 'passed',
      durationMs: 5,
      message: null,
      category: null,
    })
    const event = { type: 'run.stepResult', testId: 't1', runId: 'r1', stepIndex: 1, status: 'notRun' }
    assert.equal(stepOutcomeFrom(event)?.status, 'notRun')
    assert.equal(stepOutcomeFrom(event)?.durationMs, null)
    assert.equal(stepOutcomeFrom({ stepIndex: 0, status: 'skipped' }), null)
    assert.equal(stepOutcomeFrom({ status: 'passed' }), null)
    assert.equal(stepOutcomeFrom(null), null)
  })
})
