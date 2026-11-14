import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import { AgentNotConnectedError, AgentRpcError, AgentTimeoutError } from '../agent.ts'
import {
  describeFailure,
  ELEMENT_FROM_POINT_TIMEOUT_MS,
  elementFromPoint,
  frameRect,
  isBounds,
  listWindows,
  nativeHandle,
  parseElementHit,
  parseSnapshot,
  parseWindows,
  PICK_ACCELERATOR,
  PickHotkey,
  pickHotkeyLabel,
  MAX_SNAPSHOT_BUDGET_MS,
  snapshot,
  SNAPSHOT_MARGIN_MS,
  SNAPSHOT_TIMEOUT_MS,
} from '../spy.ts'
import { DEFAULT_SNAPSHOT_BUDGET_MS } from '../../shared/snapshot.ts'

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

  it('reports a result that is not a window list', async () => {
    assert.deepEqual(await listWindows(agentAnswering({ windows: null })), {
      ok: false,
      reason: 'bad-response',
    })
  })

  it('leaves out a window that does not match the contract', async () => {
    const result = await listWindows(
      agentAnswering({ windows: [{ ...notepad, bounds: [] }, notepad] }),
    )
    assert.deepEqual(result, { ok: true, windows: [notepad] })
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
    assert.deepEqual(describeFailure(new AgentRpcError(-32000, 'Window not found')), {
      reason: 'window-gone',
    })
    assert.deepEqual(describeFailure(new AgentRpcError(-32002, 'Snapshot timeout: blocked')), {
      reason: 'snapshot-timeout',
      detail: 'Snapshot timeout: blocked',
    })
    assert.deepEqual(describeFailure(new AgentRpcError(-32603, 'Internal error')), {
      reason: 'agent-error',
      detail: 'Internal error',
    })
    assert.deepEqual(describeFailure(new Error('boom')), { reason: 'agent-error', detail: 'boom' })
  })
})

// `dev/` is plain JavaScript outside the type-checked tree, so it is loaded by URL.
const fakeAgentEnvUrl = new URL('../../../dev/mock/fake-agent-env.mjs', import.meta.url).href
const { defaultSnapshot } = (await import(fakeAgentEnvUrl)) as { defaultSnapshot: string }

// The fake agent's tree: the schema's own example (#12), read where it lives (#204).
const trialLoginPath = join(
  import.meta.dirname,
  ...['..', '..', '..', '..'],
  ...['schemas', 'examples', 'snapshot', 'trial-login.json'],
)
const trialLogin = JSON.parse(readFileSync(trialLoginPath, 'utf8')) as {
  elements: Record<string, unknown>[]
} & Record<string, unknown>

describe('snapshot', () => {
  it('asks for the window and returns its snapshot', async () => {
    const calls: unknown[][] = []
    const result = await snapshot(agentAnswering(trialLogin, calls), 657704)
    assert.deepEqual(result, { ok: true, snapshot: trialLogin })
    assert.deepEqual(calls[0], ['snapshot', { handle: 657704 }, SNAPSHOT_TIMEOUT_MS])
  })

  it('serves the schema example in dev:mock, so there is no copy to drift (#204)', () => {
    assert.equal(defaultSnapshot, trialLoginPath)
  })

  it('sends a longer budget and waits for it (#204)', async () => {
    const calls: unknown[][] = []
    await snapshot(agentAnswering(trialLogin, calls), 657704, 30_000)
    assert.deepEqual(calls[0], [
      'snapshot',
      { handle: 657704, timeoutMs: 30_000 },
      30_000 + SNAPSHOT_MARGIN_MS,
    ])
    assert.ok(SNAPSHOT_TIMEOUT_MS > DEFAULT_SNAPSHOT_BUDGET_MS)
  })

  it('sends no budget the agent would refuse', async () => {
    for (const budget of [0, -1, 1.5, MAX_SNAPSHOT_BUDGET_MS + 1, '30000', null]) {
      const calls: unknown[][] = []
      await snapshot(agentAnswering(trialLogin, calls), 657704, budget)
      assert.deepEqual(calls[0], ['snapshot', { handle: 657704 }, SNAPSHOT_TIMEOUT_MS], `${budget}`)
    }
  })

  it('names the format of a newer snapshot instead of calling it unexpected (#204)', async () => {
    assert.deepEqual(await snapshot(agentAnswering({ ...trialLogin, version: '0.2' }), 1), {
      ok: false,
      reason: 'snapshot-version',
      detail: '0.2',
    })
  })

  it('reports a result that is not a snapshot', async () => {
    assert.deepEqual(await snapshot(agentAnswering({ ...trialLogin, elements: [] }), 1), {
      ok: false,
      reason: 'bad-response',
    })
    assert.deepEqual(await snapshot(agentAnswering({ ...trialLogin, version: 2 }), 1), {
      ok: false,
      reason: 'bad-response',
    })
  })

  it('reports a closed window and a walk over its budget', async () => {
    assert.deepEqual(await snapshot(agentAnswering(new AgentRpcError(-32000, 'gone')), 1), {
      ok: false,
      reason: 'window-gone',
    })
    assert.deepEqual(await snapshot(agentAnswering(new AgentRpcError(-32002, 'slow')), 1), {
      ok: false,
      reason: 'snapshot-timeout',
      detail: 'slow',
    })
  })
})

describe('parseSnapshot', () => {
  const [root, child] = trialLogin.elements

  it('accepts the schema example', () => {
    assert.equal(parseSnapshot(trialLogin), trialLogin)
  })

  it('rejects elements that are not one tree in pre-order', () => {
    const cases = [
      [child, root], // child before its parent
      [root, root], // repeated id
      [root, { ...root, id: 'other' }], // a second root
      [], // no root
    ]
    for (const elements of cases) {
      assert.equal(parseSnapshot({ ...trialLogin, elements }), null, JSON.stringify(elements))
    }
  })

  it('rejects malformed nodes and the fields the Spy computes with', () => {
    const cases = [
      { ...child, id: 7 },
      { ...child, parentId: undefined },
      { ...child, element: null },
      { ...child, element: { bounds: [1, 2, 3] } },
      { ...child, element: { dpi: '120' } },
    ]
    for (const node of cases) {
      const elements = [root, node]
      assert.equal(parseSnapshot({ ...trialLogin, elements }), null, JSON.stringify(node))
    }
  })

  it('rejects documents without the fields it reads', () => {
    for (const key of ['version', 'snapshotId', 'capture', 'app', 'window', 'elements']) {
      const rest = { ...trialLogin }
      delete rest[key]
      assert.equal(parseSnapshot(rest), null, key)
    }
    assert.equal(parseSnapshot({ ...trialLogin, window: {} }), null)
    assert.equal(parseSnapshot(null), null)
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

  it('reads a null title or class name as empty', () => {
    const elevated = { ...notepad, title: null, className: null }
    assert.deepEqual(parseWindows({ windows: [elevated] }), [
      { ...notepad, title: '', className: '' },
    ])
  })

  it('leaves out a window outside the contract and keeps the others', () => {
    for (const bad of [
      null,
      'window',
      { ...notepad, handle: '1' },
      { ...notepad, handle: 1.5 },
      { ...notepad, title: 5 },
      { ...notepad, className: {} },
      { ...notepad, processId: undefined },
      { ...notepad, processName: 5 },
      { ...notepad, bounds: [0, 0, 0] },
    ]) {
      assert.deepEqual(parseWindows({ windows: [bad, notepad] }), [notepad], JSON.stringify(bad))
    }
  })

  it('rejects a result that is not a window list', () => {
    for (const result of [null, [], {}, { windows: null }, { windows: {} }]) {
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

describe('PickHotkey', () => {
  /** A globalShortcut stand-in; `taken` makes registration fail like a key held elsewhere. */
  function registry(taken = false) {
    const log: string[] = []
    return {
      log,
      callbacks: [] as (() => void)[],
      register(accelerator: string, callback: () => void) {
        log.push(`register ${accelerator}`)
        this.callbacks.push(callback)
        return !taken
      },
      unregister(accelerator: string) {
        log.push(`unregister ${accelerator}`)
      },
    }
  }

  it('registers once and releases once', () => {
    const shortcuts = registry()
    let presses = 0
    const hotkey = new PickHotkey(shortcuts, () => presses++)
    assert.equal(hotkey.set(true), true)
    assert.equal(hotkey.set(true), true)
    shortcuts.callbacks[0]()
    assert.equal(presses, 1)
    assert.equal(hotkey.set(false), false)
    assert.equal(hotkey.set(false), false)
    assert.deepEqual(shortcuts.log, [
      `register ${PICK_ACCELERATOR}`,
      `unregister ${PICK_ACCELERATOR}`,
    ])
  })

  it('reports a key held by another program and does not release it', () => {
    const shortcuts = registry(true)
    const hotkey = new PickHotkey(shortcuts, () => {})
    assert.equal(hotkey.set(true), false)
    assert.equal(hotkey.set(false), false)
    assert.deepEqual(shortcuts.log, [`register ${PICK_ACCELERATOR}`])
  })

  it('names the key the way each platform writes it', () => {
    assert.equal(pickHotkeyLabel('win32'), 'Ctrl+Shift+A')
    assert.equal(pickHotkeyLabel('darwin'), '⌘⇧A')
  })
})

describe('elementFromPoint', () => {
  const hit = {
    handle: 657704,
    bounds: [614, 300, 814, 326],
    snapshotId: '5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b',
    elementId: 'e8',
    element: { name: 'Username', controlType: 'Edit', bounds: [614, 300, 814, 326] },
  }

  it('sends the point as it is and returns what the agent found', async () => {
    const calls: unknown[][] = []
    const result = await elementFromPoint(agentAnswering(hit, calls), { x: -1915, y: 312 })
    assert.deepEqual(result, { ok: true, hit })
    assert.deepEqual(calls[0], [
      'elementFromPoint',
      { x: -1915, y: 312 },
      ELEMENT_FROM_POINT_TIMEOUT_MS,
    ])
  })

  it('rounds a point that is not whole, since the agent takes integers only', async () => {
    const calls: unknown[][] = []
    await elementFromPoint(agentAnswering(hit, calls), { x: 10.6, y: -3.2 })
    assert.deepEqual(calls[0][1], { x: 11, y: -3 })
  })

  it('reports why the call failed', async () => {
    const result = await elementFromPoint(agentAnswering(new AgentRpcError(-32001, 'no backend')), {
      x: 1,
      y: 1,
    })
    assert.deepEqual(result, { ok: false, reason: 'uia-unavailable' })
  })

  it('reports an answer outside the contract', async () => {
    const result = await elementFromPoint(agentAnswering({ ...hit, bounds: [1, 2] }), {
      x: 1,
      y: 1,
    })
    assert.deepEqual(result, { ok: false, reason: 'bad-response' })
  })

  it('waits longer than a default capture, which a pick may queue behind', () => {
    assert.ok(ELEMENT_FROM_POINT_TIMEOUT_MS > DEFAULT_SNAPSHOT_BUDGET_MS)
  })
})

describe('parseElementHit', () => {
  it('accepts every state of the contract', () => {
    const nothing = { handle: null, bounds: null, snapshotId: null, elementId: null, element: null }
    assert.deepEqual(parseElementHit(nothing), nothing)
    const uncaptured = { ...nothing, handle: 66768, bounds: [0, 1040, 1920, 1080] }
    assert.deepEqual(parseElementHit(uncaptured), uncaptured)
    const changed = { ...uncaptured, snapshotId: 's1' }
    assert.deepEqual(parseElementHit(changed), changed)
  })

  it('reads a field that is left out as null', () => {
    assert.deepEqual(parseElementHit({ handle: 5 }), {
      handle: 5,
      bounds: null,
      snapshotId: null,
      elementId: null,
      element: null,
    })
  })

  it('refuses a field of the wrong type', () => {
    assert.equal(parseElementHit(null), null)
    assert.equal(parseElementHit([]), null)
    assert.equal(parseElementHit({ handle: '5' }), null)
    assert.equal(parseElementHit({ handle: 1.5 }), null)
    assert.equal(parseElementHit({ handle: 5, bounds: [3, 0, 1, 0] }), null)
    assert.equal(parseElementHit({ handle: 5, snapshotId: 7 }), null)
    assert.equal(parseElementHit({ handle: 5, elementId: 7 }), null)
    assert.equal(parseElementHit({ handle: 5, element: 'Edit' }), null)
  })
})

describe('nativeHandle', () => {
  it("reads Electron's window handle buffer, little-endian", () => {
    // 64-bit Windows: an HWND in 8 bytes.
    assert.equal(nativeHandle(Uint8Array.from([0x28, 0x09, 0x0a, 0x00, 0, 0, 0, 0])), 657704)
    // 32-bit: 4 bytes.
    assert.equal(nativeHandle(Uint8Array.from([0x28, 0x09, 0x0a, 0x00])), 657704)
    assert.equal(nativeHandle(new Uint8Array()), 0)
  })
})
