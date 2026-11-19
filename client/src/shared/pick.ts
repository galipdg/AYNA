// What a press of the Spy's pick hotkey means for the tree on screen (#24).

import type { AgentFailure, PickEvent } from './api.ts'
import type { TreeNode } from './snapshot.ts'

export type PickState =
  | { state: 'element'; node: TreeNode }
  /** Nothing of this window is captured, or not the capture on screen: offer to capture it. */
  | { state: 'not-captured'; handle: number }
  /** The window has changed since the capture on screen: offer to capture it again. */
  | { state: 'changed' }
  | { state: 'own-window' }
  | { state: 'no-window' }
  | { state: 'failed'; reason: AgentFailure; detail?: string }

/**
 * Reads a pick against the capture the Spy shows (`shown`, absent when none). The agent holds
 * the one snapshot taken last by anyone, so a `snapshotId` other than the one on screen means
 * the same as none (`docs/agent-rpc.md`, `elementFromPoint`).
 */
export function pickState(
  pick: PickEvent,
  shown: { snapshotId: string; root: TreeNode } | undefined,
): PickState {
  if (!pick.ok) {
    return pick.detail === undefined
      ? { state: 'failed', reason: pick.reason }
      : { state: 'failed', reason: pick.reason, detail: pick.detail }
  }
  if (pick.ownWindow) return { state: 'own-window' }
  const { handle, snapshotId, elementId } = pick.hit
  if (handle === null) return { state: 'no-window' }
  if (!shown || snapshotId === null || snapshotId !== shown.snapshotId) {
    return { state: 'not-captured', handle }
  }
  // An id missing from the tree cannot come from this capture; the safe reading is "changed".
  const node = elementId === null ? undefined : findNode(shown.root, elementId)
  return node ? { state: 'element', node } : { state: 'changed' }
}

/** The node with `id`, depth first without recursion: real trees nest a hundred levels deep. */
export function findNode(root: TreeNode, id: string): TreeNode | undefined {
  const stack = [root]
  for (let node = stack.pop(); node; node = stack.pop()) {
    if (node.id === id) return node
    stack.push(...node.children)
  }
  return undefined
}
