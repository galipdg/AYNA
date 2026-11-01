import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { buildTree, type SnapshotNode, type TreeNode } from '../../shared/snapshot.ts'

function node(id: string, parentId: string | null): SnapshotNode {
  return { id, parentId, element: { name: id } }
}

/** The tree as nested ids, easier to compare than whole nodes. */
function shape(tree: TreeNode): unknown {
  return tree.children.length ? { [tree.id]: tree.children.map(shape) } : tree.id
}

describe('buildTree', () => {
  it('links every element under its parent, keeping the order', () => {
    const root = buildTree([
      node('w', null),
      node('a', 'w'),
      node('a1', 'a'),
      node('a2', 'a'),
      node('b', 'w'),
    ])
    assert.ok(root)
    assert.deepEqual(shape(root), { w: [{ a: ['a1', 'a2'] }, 'b'] })
    assert.deepEqual(root.children[0].element, { name: 'a' })
  })

  it('accepts a window with no children', () => {
    assert.deepEqual(buildTree([node('w', null)]), {
      id: 'w',
      element: { name: 'w' },
      children: [],
    })
  })

  it('rejects anything that is not one tree in pre-order', () => {
    assert.equal(buildTree([]), null)
    assert.equal(buildTree([node('a', 'w'), node('w', null)]), null)
    assert.equal(buildTree([node('w', null), node('v', null)]), null)
    assert.equal(buildTree([node('w', null), node('w', 'w')]), null)
    assert.equal(buildTree([node('w', null), node('a', 'missing')]), null)
  })
})
