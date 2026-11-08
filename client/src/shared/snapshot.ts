import type { Bounds } from './api.ts'
import type { ElementDescriptor } from './element.ts'

/** The snapshot format this client reads. */
export const SNAPSHOT_VERSION = '0.1'

/** The agent's walk budget when a `snapshot` request names none (`docs/agent-rpc.md`). */
export const DEFAULT_SNAPSHOT_BUDGET_MS = 5_000

/**
 * The budgets "Capture again" sends after a walk ran out of time, one step per timeout (#204).
 * A busy window can need far more than the default: KeePass 2 took 278.5 s with one UIA reader
 * (#161) and 819 ms with another (#12). The last step repeats; the client waits for each.
 */
export const LONGER_SNAPSHOT_BUDGETS_MS = [30_000, 120_000] as const

/** The budget to try after a walk with `previous` (undefined: the default) timed out. */
export function nextSnapshotBudget(previous?: number): number {
  const longer = LONGER_SNAPSHOT_BUDGETS_MS.find((budget) => budget > (previous ?? 0))
  return longer ?? LONGER_SNAPSHOT_BUDGETS_MS[LONGER_SNAPSHOT_BUDGETS_MS.length - 1]!
}

/**
 * One window's UI Automation subtree as the agent's `snapshot` returns it:
 * `schemas/snapshot.schema.json` version 0.1 (#12, ADR 2026-11-01-snapshot-schema-v0).
 */
export interface Snapshot {
  version: '0.1'
  snapshotId: string
  capture: SnapshotCapture
  app: { exeName?: string; fileVersion?: string }
  window: SnapshotWindow
  /** Pre-order: the window's root element first, every parent before its children. */
  elements: SnapshotNode[]
}

/** What the walk cost. */
export interface SnapshotCapture {
  /** ISO 8601 with a UTC offset. */
  startedAt: string
  durationMs: number
  budgetMs: number
  elementCount: number
  /** Single property reads that failed; a high count means a thin tree, not a failed walk. */
  readErrors?: number
  agentVersion?: string
  featureVersion: string
}

/** The captured window's identity, with the fields `listWindows` reports for it. */
export interface SnapshotWindow {
  handle: number
  title?: string
  className?: string
  processId?: number
  bounds?: Bounds
  dpi?: number
}

export interface SnapshotNode {
  /** Opaque, unique within the snapshot; compare only for equality. */
  id: string
  /** Null for the window's root element only. */
  parentId: string | null
  element: ElementDescriptor
}

export interface TreeNode {
  id: string
  element: ElementDescriptor
  children: TreeNode[]
}

/**
 * Builds the tree in one pass over the list. Null when the list is not one tree with each
 * parent before its children: no root or a second one, a repeated id, or a parent that comes
 * later. That is weaker than the schema's pre-order (the server and the agent also refuse a
 * subtree that is not contiguous), so the Spy showing a document does not mean the server
 * accepts it.
 */
export function buildTree(elements: readonly SnapshotNode[]): TreeNode | null {
  const byId = new Map<string, TreeNode>()
  let root: TreeNode | null = null
  for (const { id, parentId, element } of elements) {
    if (byId.has(id)) return null
    const node: TreeNode = { id, element, children: [] }
    if (parentId === null) {
      if (root) return null
      root = node
    } else {
      const parent = byId.get(parentId)
      if (!parent) return null
      parent.children.push(node)
    }
    byId.set(id, node)
  }
  return root
}
