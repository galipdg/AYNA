import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { AgentNotConnectedError, AgentRpcError, AgentTimeoutError } from '../agent.ts'
import { describeFailure, frameRect, isBounds, listWindows, parseWindows } from '../spy.ts'

const notepad = {
  handle: 395942,
  title: 'Untitled - Notepad',
  className: 'Notepad',
  processId: 7316,
  processName: 'notepad.exe',
  bounds: [320, 180, 960, 660],
}

/** An agent stub that answers every call with `answer` (or throws it). */
function agentAnswering(answer: unknown, calls: unknown[][] = []) {
  return {
    call: async (...args: unknown[]) => {
      calls.push(args)
      if (answer instanceof Error) throw answer
      return answer
    },
  }
}

describe('listWindows', () => {
  it('returns the windows the agent lists', async () => {
    const calls: unknown[][] = []
    const result = await listWindows(agentAnswering({ windows: [notepad] }, calls))
    assert.deepEqual(result, { ok: true, windows: [notepad] })
    assert.equal(calls[0][0], 'listWindows')
  })

  it('reports a result that does not match the contract', async () => {
    assert.deepEqual(await listWindows(agentAnswering({ windows: [{ ...notepad, bounds: [] }] })), {
      ok: false,
      reason: 'bad-response',
    })
  })

  it('reports why the call failed', async () => {
    const result = await listWindows(
      agentAnswering(new AgentRpcError(-32001, 'UI Automation unavailable: no backend')),
    )
    assert.deepEqual(result, { ok: false, reason: 'uia-unavailable' })
  })
})

describe('describeFailure', () => {
  it('maps each agent error to a reason', () => {
    assert.deepEqual(describeFailure(new AgentNotConnectedError()), { reason: 'not-connected' })
    assert.deepEqual(describeFailure(new AgentNotConnectedError('the agent stopped')), {
      reason: 'not-connected',
    })
    assert.deepEqual(describeFailure(new AgentTimeoutError('listWindows', 10)), {
      reason: 'timeout',
    })
    assert.deepEqual(describeFailure(new AgentRpcError(-32001, 'no backend')), {
      reason: 'uia-unavailable',
    })
    assert.deepEqual(describeFailure(new AgentRpcError(-32603, 'Internal error')), {
      reason: 'agent-error',
      detail: 'Internal error',
    })
    assert.deepEqual(describeFailure(new Error('boom')), { reason: 'agent-error', detail: 'boom' })
  })
})

describe('parseWindows', () => {
  it('accepts an empty list, a null process name and negative coordinates', () => {
    assert.deepEqual(parseWindows({ windows: [] }), [])
    const left = { ...notepad, processName: null, bounds: [-1920, -200, -1000, 400] }
    assert.deepEqual(parseWindows({ windows: [left] }), [left])
  })

  it('drops fields outside the contract', () => {
    assert.deepEqual(parseWindows({ windows: [{ ...notepad, extra: 1 }] }), [notepad])
  })

  it('rejects anything else', () => {
    for (const result of [
      null,
      [],
      { windows: null },
      { windows: [null] },
      { windows: [{ ...notepad, handle: '1' }] },
      { windows: [{ ...notepad, handle: 1.5 }] },
      { windows: [{ ...notepad, title: null }] },
      { windows: [{ ...notepad, processId: undefined }] },
      { windows: [{ ...notepad, processName: 5 }] },
    ]) {
      assert.equal(parseWindows(result), null, JSON.stringify(result))
    }
  })
})

describe('isBounds', () => {
  it('needs four integers with left <= right and top <= bottom', () => {
    assert.ok(isBounds([0, 0, 0, 0]))
    assert.ok(isBounds([-10, -10, 10, 10]))
    for (const value of [
      null,
      [0, 0, 0],
      [0, 0, 0, 0, 0],
      [0, 0, 1.5, 1],
      [5, 0, 1, 1],
      [0, 5, 1, 1],
      ['0', 0, 1, 1],
    ]) {
      assert.equal(isBounds(value), false, JSON.stringify(value))
    }
  })
})

describe('frameRect', () => {
  const identity = (rect: { x: number; y: number; width: number; height: number }) => rect

  it('surrounds the element with the border', () => {
    assert.deepEqual(frameRect([100, 50, 300, 80], identity, 3), {
      x: 97,
      y: 47,
      width: 206,
      height: 36,
    })
  })

  it('converts physical pixels to DIPs before adding the border', () => {
    // 150 % scaling: 1.5 physical pixels per DIP.
    const scale150 = (rect: { x: number; y: number; width: number; height: number }) => ({
      x: rect.x / 1.5,
      y: rect.y / 1.5,
      width: rect.width / 1.5,
      height: rect.height / 1.5,
    })
    assert.deepEqual(frameRect([300, 150, 600, 195], scale150, 3), {
      x: 197,
      y: 97,
      width: 206,
      height: 36,
    })
  })
})
