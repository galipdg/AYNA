import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { ElementHit, PickEvent } from '../../shared/api.ts'
import type { ElementDescriptor } from '../../shared/element.ts'
import { findNode, pickState } from '../../shared/pick.ts'
import type { TreeNode } from '../../shared/snapshot.ts'

function node(id: string, element: ElementDescriptor, children: TreeNode[] = []): TreeNode {
  return { id, element, children }
}

// window
// ├─ Edit "Username"
// └─ Group
//    └─ Button "Login"
const login = node('e3', { controlType: 'Button', name: 'Login' })
const root = node('e0', { controlType: 'Window', name: 'AYNA Trial' }, [
  node('e1', { controlType: 'Edit', name: 'Username' }),
  node('e2', { controlType: 'Group' }, [login]),
])
const shown = { snapshotId: 's1', root }

const point = { x: 785, y: 312 }
const nothing: ElementHit = {
  handle: null,
  bounds: null,
  snapshotId: null,
  elementId: null,
  element: null,
}
const inWindow: ElementHit = { ...nothing, handle: 657704, bounds: [600, 290, 830, 340] }

function picked(hit: ElementHit, ownWindow = false): PickEvent {
  return { point, ok: true, hit, ownWindow }
}

describe('pickState', () => {
  it('selects the node the agent named in the snapshot on screen', () => {
    const hit = { ...inWindow, snapshotId: 's1', elementId: 'e3', element: login.element }
    assert.deepEqual(pickState(picked(hit), shown), { state: 'element', node: login })
  })

  it('offers a capture when the agent holds no snapshot of that window', () => {
    assert.deepEqual(pickState(picked({ ...inWindow }), shown), {
      state: 'not-captured',
      handle: 657704,
    })
  })

  it('treats a snapshot other than the one on screen like none at all', () => {
    // A repository import (#15) or a capture of another window replaced the Spy's.
    const hit = { ...inWindow, snapshotId: 's2', elementId: 'e3', element: login.element }
    assert.deepEqual(pickState(picked(hit), shown), { state: 'not-captured', handle: 657704 })
    assert.deepEqual(pickState(picked(hit), undefined), {
      state: 'not-captured',
      handle: 657704,
    })
  })

  it('offers "capture again" when the window changed since the capture', () => {
    const hit = { ...inWindow, snapshotId: 's1' }
    assert.deepEqual(pickState(picked(hit), shown), { state: 'changed' })
  })

  it('reads an element id missing from the tree on screen as a changed window', () => {
    const hit = { ...inWindow, snapshotId: 's1', elementId: 'e99', element: login.element }
    assert.deepEqual(pickState(picked(hit), shown), { state: 'changed' })
  })

  it("ignores AYNA's own windows", () => {
    const hit = { ...inWindow, snapshotId: 's1', elementId: 'e3', element: login.element }
    assert.deepEqual(pickState(picked(hit, true), shown), { state: 'own-window' })
  })

  it('says when there is no window under the cursor', () => {
    assert.deepEqual(pickState(picked(nothing), shown), { state: 'no-window' })
  })

  it('passes on why the call failed', () => {
    const failed: PickEvent = { point, ok: false, reason: 'uia-unavailable' }
    assert.deepEqual(pickState(failed, shown), { state: 'failed', reason: 'uia-unavailable' })
    const timeout: PickEvent = { point, ok: false, reason: 'agent-error', detail: 'boom' }
    assert.deepEqual(pickState(timeout, shown), {
      state: 'failed',
      reason: 'agent-error',
      detail: 'boom',
    })
  })
})

describe('findNode', () => {
  it('finds a node at any depth, and nothing for an unknown id', () => {
    assert.equal(findNode(root, 'e0'), root)
    assert.equal(findNode(root, 'e3'), login)
    assert.equal(findNode(root, 'nope'), undefined)
  })

  it('walks a deep tree without recursion', () => {
    let deep = node('leaf', { controlType: 'Text' })
    for (let i = 0; i < 20_000; i++) deep = node(`n${i}`, { controlType: 'Pane' }, [deep])
    assert.equal(findNode(deep, 'leaf')?.id, 'leaf')
  })
})
