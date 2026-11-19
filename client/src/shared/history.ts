// Undo and redo for the step editor (#196). Kept free of React, so plain `node --test` can use it.

export const HISTORY_LIMIT = 100

/** Keystrokes in one field closer together than this undo as one change. */
export const TYPING_GAP_MS = 1000

export interface History<T> {
  past: T[]
  present: T
  future: T[]
  /** The field the last change typed into, and when; the next keystroke there joins it. */
  typing?: { group: string; at: number }
}

export function startHistory<T>(present: T): History<T> {
  return { past: [], present, future: [] }
}

/**
 * Adds a change. `group` names a text field: keystrokes in it join one change until the user
 * pauses or goes elsewhere. A change that changed nothing is not recorded.
 */
export function record<T>(
  history: History<T>,
  next: T,
  group?: string,
  now: number = Date.now(),
): History<T> {
  if (next === history.present) return history
  const typing = group === undefined ? undefined : { group, at: now }
  const last = history.typing
  if (group !== undefined && last?.group === group && now - last.at < TYPING_GAP_MS) {
    return { ...history, present: next, future: [], typing }
  }
  const past = [...history.past, history.present].slice(-HISTORY_LIMIT)
  return { past, present: next, future: [], typing }
}

export function undo<T>(history: History<T>): History<T> {
  if (history.past.length === 0) return history
  return {
    past: history.past.slice(0, -1),
    present: history.past[history.past.length - 1],
    future: [history.present, ...history.future],
  }
}

export function redo<T>(history: History<T>): History<T> {
  if (history.future.length === 0) return history
  return {
    past: [...history.past, history.present],
    present: history.future[0],
    future: history.future.slice(1),
  }
}

/** The same history with every state changed, for what a save makes out of date. */
export function mapHistory<T>(history: History<T>, change: (state: T) => T): History<T> {
  return {
    ...history,
    past: history.past.map(change),
    present: change(history.present),
    future: history.future.map(change),
  }
}

export type HistoryCommand = 'undo' | 'redo'

/** Ctrl+Z or ⌘Z undoes; Ctrl+Y, Ctrl+Shift+Z or ⇧⌘Z redoes. */
export function historyCommand(event: {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  shiftKey: boolean
  altKey: boolean
}): HistoryCommand | null {
  if ((!event.ctrlKey && !event.metaKey) || event.altKey) return null
  const key = event.key.toLowerCase()
  if (key === 'z') return event.shiftKey ? 'redo' : 'undo'
  return key === 'y' && !event.shiftKey ? 'redo' : null
}
