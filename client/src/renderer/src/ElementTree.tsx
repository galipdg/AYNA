import { useState, type ReactElement } from 'react'
import type { TreeNode } from '../../shared/snapshot.ts'
import { strings } from './strings.ts'

/** Levels open when a snapshot arrives: the window and its direct children. */
const OPEN_DEPTH = 1

function openUpTo(node: TreeNode, depth: number, open = new Set<string>()): Set<string> {
  if (depth < 0 || node.children.length === 0) return open
  open.add(node.id)
  for (const child of node.children) openUpTo(child, depth - 1, open)
  return open
}

/** Like other spy tools: control type, then the name, else the AutomationId. */
function Caption({ node }: { node: TreeNode }) {
  const { controlType, name, automationId } = node.element
  return (
    <>
      <span className="control-type">{controlType ?? strings.spyUnknownControlType}</span>
      {name !== undefined && <span>“{name}”</span>}
      {name === undefined && automationId !== undefined && (
        <span className="automation-id">{automationId}</span>
      )}
    </>
  )
}

/**
 * A window's element tree, collapsible per node. Mount it with a `key` per snapshot so a
 * new capture starts from the default open levels.
 */
export default function ElementTree({
  root,
  selectedId,
  onSelect,
}: {
  root: TreeNode
  selectedId?: string
  onSelect: (node: TreeNode) => void
}) {
  const [open, setOpen] = useState(() => openUpTo(root, OPEN_DEPTH))

  function toggle(id: string) {
    setOpen((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })
  }

  function item(node: TreeNode): ReactElement {
    const isOpen = open.has(node.id)
    const hasChildren = node.children.length > 0
    return (
      <li key={node.id}>
        <div className="row">
          {hasChildren ? (
            <button
              type="button"
              className="toggle"
              aria-expanded={isOpen}
              aria-label={isOpen ? strings.spyCollapse : strings.spyExpand}
              onClick={() => toggle(node.id)}
            >
              {isOpen ? '▾' : '▸'}
            </button>
          ) : (
            <span className="toggle" />
          )}
          <button
            type="button"
            className={node.id === selectedId ? 'node selected' : 'node'}
            aria-pressed={node.id === selectedId}
            onClick={() => onSelect(node)}
          >
            <Caption node={node} />
          </button>
        </div>
        {hasChildren && isOpen && <ul>{node.children.map(item)}</ul>}
      </li>
    )
  }

  return (
    <ul className="spy-tree" aria-label={strings.spyTreeTitle}>
      {item(root)}
    </ul>
  )
}
