import type { ElementDescriptor } from './element.ts'
import type { TreeNode } from './snapshot.ts'

/** One line of the Spy's element tree as it is drawn: the node and how deep it sits. */
export interface TreeRow {
  node: TreeNode
  depth: number
  open: boolean
}

/**
 * Form for search that ignores case and the Turkish letters people type as ASCII: "giris"
 * finds "Giriş", "degistir" finds "Değiştir", "kullanici" finds "Kullanıcı" and "id" finds
 * "ID". ş ğ ü ö ç decompose under NFD into a base letter and a mark, which is dropped; ı has
 * no mark, so the i's are folded first (a Turkish locale alone would turn "I" into "ı" and
 * miss "ID").
 */
export function foldText(text: string): string {
  return text
    .replace(/[İIı]/g, 'i')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

/**
 * The last part of a dotted AutomationId. Qt builds the id from the object names of every
 * ancestor ("QApplication.loginWindow.loginButton"), so the window's own part matches every
 * element in it; the last part is what names this element (#204).
 */
export function automationIdLeaf(id: string): string {
  return id.slice(id.lastIndexOf('.') + 1)
}

/**
 * Whether an element matches a search, by name, control type, AutomationId or nearest label.
 * The label is what finds a text box with no name of its own (common in Qt and WinForms) by the
 * caption next to it. `typeLabel` adds the type's plain-language label, so "text box" finds
 * Edit elements too. The AutomationId is searched by its last part, unless the query has a dot
 * of its own (a pasted id).
 */
export function elementMatches(
  element: ElementDescriptor,
  query: string,
  typeLabel?: (controlType: string) => string,
): boolean {
  const needle = foldText(query.trim())
  if (!needle) return true
  const { name, controlType, automationId, nearestLabel } = element
  const haystack = [
    name,
    controlType,
    automationId !== undefined && !needle.includes('.')
      ? automationIdLeaf(automationId)
      : automationId,
    nearestLabel,
    controlType && typeLabel?.(controlType),
  ]
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
