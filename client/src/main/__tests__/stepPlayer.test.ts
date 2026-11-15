import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { AgentNotConnectedError, AgentRpcError, AgentTimeoutError } from '../agent.ts'
import { perStepPlayer, type PlayRequest } from '../stepPlayer.ts'

function request(overrides: Partial<PlayRequest> = {}): PlayRequest {
  return {
    step: { keyword: 'Click', target: 'login.okButton' },
    stepIndex: 4,
    stepId: 's5',
    version: '0.2',
    handle: 657704,
    target: { properties: { automationId: 'okButton' }, fallback: { name: 'OK' } },
    runId: 'r1',
    appVersionId: 'v1',
    ...overrides,
  }
}

/** An agent that answers every call with `answer`, or throws it if it is an Error. */
function agent(answer: unknown, calls: unknown[][] = []) {
  return {
    async call(...args: unknown[]) {
      calls.push(args)
      if (answer instanceof Error) throw answer
      return answer
    },
  }
}

describe('the per-step player', () => {
  it('sends one step with its one target', async () => {
    const calls: unknown[][] = []
    const passed = { results: [{ stepIndex: 0, status: 'passed', durationMs: 31 }] }
    await perStepPlayer(agent(passed, calls)).play(request())
    const [method, params, timeoutMs] = calls[0]
    assert.equal(method, 'runSteps')
    assert.deepEqual(params, {
      handle: 657704,
      steps: { version: '0.2', steps: [{ keyword: 'Click', target: 'login.okButton' }] },
      targets: { 'login.okButton': { properties: { automationId: 'okButton' }, fallback: { name: 'OK' } } },
      runId: 'r1',
      appVersionId: 'v1',
    })
    assert.equal(timeoutMs, 10_000 + 10_000)
    await perStepPlayer(agent(passed, calls)).play(
      request({ step: { keyword: 'Wait', target: 'main.menu', timeoutMs: 2000 } }),
    )
    assert.equal(calls[1][2], 2000 + 10_000)
  })

  it("puts the run's index on the result", async () => {
    const answer = {
      results: [{ stepIndex: 0, status: 'failed', durationMs: 12, message: 'gone', category: 'elementNotFound' }],
    }
    const played = await perStepPlayer(agent(answer)).play(request())
    assert.deepEqual(played, {
      outcome: {
        stepIndex: 4,
        stepId: 's5',
        status: 'failed',
        durationMs: 12,
        message: 'gone',
        category: 'elementNotFound',
      },
      agentGone: false,
    })
  })

  it('turns agent errors into a failed step', async () => {
    const cases: [unknown, boolean, string | null][] = [
      [new AgentNotConnectedError(), true, null],
      [new AgentTimeoutError('runSteps', 20_000), false, null],
      [new AgentRpcError(-32000, 'no such window'), false, null],
      [new AgentRpcError(-32002, 'window read ran out of time'), false, 'searchIncomplete'],
      [{ results: [] }, false, null],
      [{ nonsense: true }, false, null],
    ]
    for (const [answer, gone, category] of cases) {
      const played = await perStepPlayer(agent(answer)).play(request())
      const label = answer instanceof Error ? answer.name : JSON.stringify(answer)
      assert.equal(played.outcome.status, 'failed', label)
      assert.equal(played.outcome.stepIndex, 4, label)
      assert.ok(played.outcome.message, label)
      assert.equal(played.outcome.category, category, label)
      assert.equal(played.agentGone, gone, label)
    }
  })
})
