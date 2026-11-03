import type { ElementDescriptor } from './element.ts'
import type { TreeNode } from './snapshot.ts'

/** One line of the Spy's element tree as it is drawn: the node and how deep it sits. */
export interface TreeRow {
  node: TreeNode
  depth: number
  open: boolean
}

/**
 * Case-insensitive form for search that also ignores the Turkish dotted/dotless i, so
 * "kullanici" finds "Kullanıcı" and "id" finds "ID" (a Turkish locale alone would turn
 * "I" into "ı" and miss the second).
 */
export function foldText(text: string): string {
  return text.replace(/[İIı]/g, 'i').toLowerCase()
}

/**
 * Whether an element matches a search, by name, control type or AutomationId. `typeLabel`
 * adds the type's plain-language label, so "text box" finds Edit elements too.
 */
export function elementMatches(
  element: ElementDescriptor,
  query: string,
  typeLabel?: (controlType: string) => string,
): boolean {
  const needle = foldText(query.trim())
  if (!needle) return true
  const { name, controlType, automationId } = element
  const haystack = [name, controlType, automationId, controlType && typeLabel?.(controlType)]
  return haystack.some((text) => text !== undefined && foldText(text).includes(needle))
}

/** Every node's parent (null for the root), for revealing a node and moving left. */
export function parentMap(root: TreeNode): Map<string, TreeNode | null> {
  const parents = new Map<string, TreeNode | null>([[root.id, null]])
  const stack = [root]
  while (stack.length) {
    const node = stack.pop()!
    for (const child of node.children) {
      parents.set(child.id, node)
      stack.push(child)
    }
  }
  return parents
}

/** Ids of the node's ancestors, nearest first. */
export function ancestorIds(id: string, parents: Map<string, TreeNode | null>): string[] {
  const ids: string[] = []
  for (let parent = parents.get(id); parent; parent = parents.get(parent.id)) ids.push(parent.id)
  return ids
}

/**
 * The search result: matching nodes, and the nodes to draw (matches and their ancestors).
 * Null for an empty query.
 */
export function searchTree(
  root: TreeNode,
  query: string,
  typeLabel?: (controlType: string) => string,
): { matches: Set<string>; shown: Set<string> } | null {
  if (!query.trim()) return null
  const parents = parentMap(root)
  const matches = new Set<string>()
  const shown = new Set<string>()
  const stack = [root]
  while (stack.length) {
    const node = stack.pop()!
    if (elementMatches(node.element, query, typeLabel)) {
      matches.add(node.id)
      shown.add(node.id)
      for (const id of ancestorIds(node.id, parents)) shown.add(id)
    }
    stack.push(...node.children)
  }
  return { matches, shown }
}

/**
 * The rows to draw, in tree order: open nodes show their children. With a search, only
 * `shown` nodes are drawn and they are all open, so every match is visible. Iterative, so
 * deep trees do not exhaust the stack.
 */
export function visibleRows(root: TreeNode, open: Set<string>, shown?: Set<string>): TreeRow[] {
  const rows: TreeRow[] = []
  const stack: { node: TreeNode; depth: number }[] = [{ node: root, depth: 0 }]
  while (stack.length) {
    const { node, depth } = stack.pop()!
    if (shown && !shown.has(node.id)) continue
    const isOpen = shown ? true : open.has(node.id)
    rows.push({ node, depth, open: isOpen && node.children.length > 0 })
    if (!isOpen) continue
    for (let i = node.children.length - 1; i >= 0; i--) {
      stack.push({ node: node.children[i]!, depth: depth + 1 })
    }
  }
  return rows
}
