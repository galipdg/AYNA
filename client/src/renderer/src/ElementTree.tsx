import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import type { TreeNode } from '../../shared/snapshot.ts'
import {
  ancestorIds,
  deepestRow,
  parentMap,
  searchTree,
  visibleRows,
  type TreeRow,
} from '../../shared/tree.ts'
import { controlTypeLabel, strings } from './strings.ts'

/** Levels open when a snapshot arrives: the window and its direct children. */
const OPEN_DEPTH = 1
/** Fixed row height in px; only the rows in view are drawn, so thousands of elements stay fast. */
const ROW_HEIGHT = 28
/** Rows drawn above and below the visible ones, so fast scrolling shows no gaps. */
const OVERSCAN = 10
/** Indent per level, px. */
const INDENT = 16
/** Room after a row's indent for the toggle and the caption; a longer caption ends in "…". */
const CAPTION_WIDTH = 300

function openUpTo(node: TreeNode, depth: number, open = new Set<string>()): Set<string> {
  if (depth < 0 || node.children.length === 0) return open
  open.add(node.id)
  for (const child of node.children) openUpTo(child, depth - 1, open)
  return open
}

/**
 * The element's text, else its AutomationId, then its type in plain words. An element with
 * neither is named by its type alone: a quarter of a Chromium window is unnamed Group, Pane and
 * ToolBar wrappers (#184), and rows saying "(no name)" told the user nothing (#204).
 */
function Caption({ node }: { node: TreeNode }) {
  const { controlType, name, automationId } = node.element
  const type = controlTypeLabel(controlType)
  if (name === undefined && automationId === undefined) {
    return <span className="node-name node-unnamed">{type}</span>
  }
  return (
    <>
      {name !== undefined ? (
        <span className="node-name" title={name}>
          {name}
        </span>
      ) : (
        <span className="node-name automation-id" title={automationId}>
          {automationId}
        </span>
      )}
      <span className="node-type">{type}</span>
    </>
  )
}

const rowId = (id: string) => `tree-row-${id}`

/**
 * A window's element tree with search (by name, type or AutomationId) and keyboard moves.
 * Only the visible rows are rendered. The chosen element is kept in view and its ancestors
 * opened. Mount it with a `key` per snapshot so a new capture starts from the default levels.
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
  const [query, setQuery] = useState('')
  const [scrollTop, setScrollTop] = useState(0)
  const [height, setHeight] = useState(400)
  const viewport = useRef<HTMLDivElement>(null)

  const parents = useMemo(() => parentMap(root), [root])
  // The control types of the current language: a language change searches again.
  const types = strings.controlTypes
  const search = useMemo(
    () => searchTree(root, query, (type) => types[type] ?? type),
    [root, query, types],
  )
  // The chosen element stays in the tree during a search, even when it does not match.
  const shown = useMemo(
    () =>
      search && selectedId !== undefined && parents.has(selectedId)
        ? new Set([...search.shown, selectedId, ...ancestorIds(selectedId, parents)])
        : search?.shown,
    [search, selectedId, parents],
  )
  const rows = useMemo(() => visibleRows(root, open, shown), [root, open, shown])
  // The scrollable width fits the deepest row of all, drawn or not. Taken from the rows drawn,
  // it changed at nearly every scroll step of a real window, whose depth varies from row to
  // row (VS Code: 285 elements, 102 nested groups, #184 step 6).
  const width = useMemo(() => 4 + deepestRow(rows) * INDENT + CAPTION_WIDTH, [rows])
  const selectedIndex = rows.findIndex((row) => row.node.id === selectedId)

  // A selection made elsewhere (the pick hotkey) may sit in a folded branch: open its
  // ancestors once per new selection, so the user can still fold them afterwards.
  const [revealed, setRevealed] = useState(selectedId)
  if (selectedId !== revealed) {
    setRevealed(selectedId)
    if (selectedId !== undefined) {
      const hidden = ancestorIds(selectedId, parents).filter((id) => !open.has(id))
      if (hidden.length) setOpen(new Set([...open, ...hidden]))
    }
  }

  // Keep the chosen row in view when the selection or the search changes.
  const scrolledFor = useRef<string>(undefined)
  useEffect(() => {
    const key = `${selectedId}|${query}`
    const box = viewport.current
    if (!box || selectedIndex < 0 || scrolledFor.current === key) return
    scrolledFor.current = key
    const top = selectedIndex * ROW_HEIGHT
    if (top < box.scrollTop) box.scrollTop = top
    else if (top + ROW_HEIGHT > box.scrollTop + box.clientHeight) {
      box.scrollTop = top + ROW_HEIGHT - box.clientHeight
    }
  }, [selectedId, query, selectedIndex])

  useEffect(() => {
    const box = viewport.current
    if (!box) return
    const observer = new ResizeObserver(() => setHeight(box.clientHeight))
    observer.observe(box)
    return () => observer.disconnect()
  }, [])

  function toggle(id: string) {
    setOpen((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })
  }

  function select(row: TreeRow | undefined) {
    if (row) onSelect(row.node)
  }

  function key(event: KeyboardEvent) {
    const row = rows[selectedIndex]
    const moves: Record<string, () => void> = {
      ArrowDown: () => select(rows[Math.min(selectedIndex + 1, rows.length - 1)]),
      ArrowUp: () => select(rows[Math.max(selectedIndex - 1, 0)]),
      Home: () => select(rows[0]),
      End: () => select(rows.at(-1)),
      ArrowRight: () => {
        if (!row || row.node.children.length === 0) return
        if (!row.open && !search) toggle(row.node.id)
        else select(rows[selectedIndex + 1])
      },
      ArrowLeft: () => {
        if (!row) return
        if (row.open && !search) return toggle(row.node.id)
        const parent = parents.get(row.node.id)
        if (parent) onSelect(parent)
      },
    }
    const move = moves[event.key]
    if (!move) return
    event.preventDefault()
    move()
  }

  const first = Math.max(Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN, 0)
  const last = Math.min(Math.ceil((scrollTop + height) / ROW_HEIGHT) + OVERSCAN, rows.length)
  return (
    <div className="tree">
      <div className="tree-search">
        <input
          type="search"
          aria-label={strings.spySearchTree}
          placeholder={strings.spySearchTree}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {search && <span className="hint">{strings.spyMatchCount(search.matches.size)}</span>}
      </div>
      {search?.matches.size === 0 && (
        <p className="hint tree-empty">{strings.spyNoElementMatch(query.trim())}</p>
      )}
      <div
        className="tree-viewport"
        ref={viewport}
        role="tree"
        aria-label={strings.spyTreeTitle}
        aria-activedescendant={selectedId ? rowId(selectedId) : undefined}
        tabIndex={0}
        onKeyDown={key}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        <div
          className="tree-canvas"
          style={{ height: rows.length * ROW_HEIGHT, width: `max(100%, ${width}px)` }}
        >
          <ul style={{ transform: `translateY(${first * ROW_HEIGHT}px)` }}>
            {rows.slice(first, last).map((row) => {
              const { node, depth } = row
              const selected = node.id === selectedId
              const hasChildren = node.children.length > 0
              return (
                <li
                  key={node.id}
                  id={rowId(node.id)}
                  role="treeitem"
                  aria-level={depth + 1}
                  aria-selected={selected}
                  aria-expanded={hasChildren ? row.open : undefined}
                  className={[
                    'tree-row',
                    selected && 'selected',
                    search?.matches.has(node.id) && 'match',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  style={{ paddingLeft: 4 + depth * INDENT }}
                  onClick={() => onSelect(node)}
                >
                  <span
                    className="toggle"
                    aria-hidden="true"
                    onClick={(event) => {
                      if (!hasChildren || search) return
                      event.stopPropagation()
                      toggle(node.id)
                    }}
                  >
                    {hasChildren ? (row.open ? '▾' : '▸') : ''}
                  </span>
                  <Caption node={node} />
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
