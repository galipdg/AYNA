import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import {
  buildTree,
  LONGER_SNAPSHOT_BUDGETS_MS,
  nextSnapshotBudget,
  SNAPSHOT_VERSION,
  type Snapshot,
  type SnapshotCapture,
  type SnapshotNode,
  type SnapshotWindow,
  type TreeNode,
} from '../../shared/snapshot.ts'
import { parseSnapshot } from '../spy.ts'

const examples = join(import.meta.dirname, '..', '..', '..', '..', 'schemas')
const read = (...path: string[]) => JSON.parse(readFileSync(join(examples, ...path), 'utf8'))

const schema = read('snapshot.schema.json') as {
  properties: Record<string, unknown> & { version: { const: string } }
  $defs: Record<string, { properties: Record<string, unknown> }>
}

// `satisfies` makes typecheck fail when a type gains or loses a field; the test below
// compares the same keys with the schema file, so the types and the schema cannot drift.
const snapshotKeys = {
  version: true,
  snapshotId: true,
  capture: true,
  app: true,
  window: true,
  elements: true,
} satisfies Record<keyof Snapshot, true>
const captureKeys = {
  startedAt: true,
  durationMs: true,
  budgetMs: true,
  elementCount: true,
  readErrors: true,
  agentVersion: true,
  featureVersion: true,
} satisfies Record<keyof SnapshotCapture, true>
const appKeys = { exeName: true, fileVersion: true } satisfies Record<keyof Snapshot['app'], true>
const windowKeys = {
  handle: true,
  title: true,
  className: true,
  processId: true,
  bounds: true,
  dpi: true,
} satisfies Record<keyof SnapshotWindow, true>
const nodeKeys = { id: true, parentId: true, element: true } satisfies Record<
  keyof SnapshotNode,
  true
>

const keys = (o: object) => Object.keys(o).sort()

describe('snapshot types', () => {
  it('have exactly the fields of schemas/snapshot.schema.json', () => {
    assert.equal(schema.properties.version.const, '0.1')
    assert.deepEqual(keys(snapshotKeys), keys(schema.properties))
    assert.deepEqual(keys(captureKeys), keys(schema.$defs.capture.properties))
    assert.deepEqual(keys(appKeys), keys(schema.$defs.app.properties))
    assert.deepEqual(keys(windowKeys), keys(schema.$defs.window.properties))
    assert.deepEqual(keys(nodeKeys), keys(schema.$defs.node.properties))
  })
})

type Operation = { op: 'add' | 'remove' | 'replace'; path: string; value?: unknown }

/** RFC 6902 add, remove and replace: all that `cases.json` uses. */
function patched(base: unknown, patch: Operation[]): unknown {
  const document = structuredClone(base)
  for (const { op, path, value } of patch) {
    const parts = path
      .split('/')
      .slice(1)
      .map((p) => p.replaceAll('~1', '/').replaceAll('~0', '~'))
    const key = parts.pop()!
    let parent = document as Record<string, unknown>
    for (const part of parts) parent = parent[part] as Record<string, unknown>
    if (Array.isArray(parent)) {
      const index = key === '-' ? parent.length : Number(key)
      if (op === 'remove') parent.splice(index, 1)
      else parent.splice(index, op === 'replace' ? 1 : 0, structuredClone(value))
    } else if (op === 'remove') {
      delete parent[key]
    } else {
      parent[key] = structuredClone(value)
    }
  }
  return document
}

describe('parseSnapshot on the shared examples', () => {
  const base = read('examples', 'snapshot', 'trial-login.json')
  const cases = read('examples', 'snapshot', 'cases.json') as {
    valid: { name: string; patch: Operation[] }[]
  }

  it('accepts the trial-app snapshot from #12', () => {
    assert.equal(parseSnapshot(base), base)
  })

  it('accepts every valid case', () => {
    for (const { name, patch } of cases.valid) {
      assert.notEqual(parseSnapshot(patched(base, patch)), null, name)
    }
  })
})

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

describe('nextSnapshotBudget (#204)', () => {
  it('steps up after each timeout and stays at the last step', () => {
    assert.equal(nextSnapshotBudget(undefined), 30_000)
    assert.equal(nextSnapshotBudget(30_000), 120_000)
    assert.equal(nextSnapshotBudget(120_000), 120_000)
    assert.equal(nextSnapshotBudget(45_000), 120_000)
  })

  it('stays inside what the agent takes', () => {
    assert.ok(LONGER_SNAPSHOT_BUDGETS_MS.every((ms) => ms >= 1 && ms <= 600_000))
  })

  it('reads the version the schema pins', () => {
    const schemaPath = join(
      import.meta.dirname,
      '..',
      '..',
      '..',
      '..',
      'schemas',
      'snapshot.schema.json',
    )
    const schema = JSON.parse(readFileSync(schemaPath, 'utf8'))
    assert.equal(schema.properties.version.const, SNAPSHOT_VERSION)
  })
})
