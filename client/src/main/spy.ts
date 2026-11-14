// The Spy's calls to the local agent, turned into plain results for the renderer.
// Free of Electron imports so `node --test` can run it against a stub agent.

import type {
  AgentFailure,
  Bounds,
  ElementFromPointResult,
  ElementHit,
  ScreenPoint,
  SnapshotResult,
  WindowInfo,
  WindowsResult,
} from '../shared/api.ts'
import {
  buildTree,
  DEFAULT_SNAPSHOT_BUDGET_MS,
  SNAPSHOT_VERSION,
  type Snapshot,
  type SnapshotNode,
} from '../shared/snapshot.ts'
import { AgentNotConnectedError, AgentRpcError, AgentTimeoutError } from './agent.ts'

/** The part of `AgentManager` the Spy needs. */
export interface AgentCaller {
  call(method: string, params?: Record<string, unknown>, timeoutMs?: number): Promise<unknown>
}

// Error codes of `docs/agent-rpc.md`.
/** No top-level window has the handle (any more). */
export const WINDOW_NOT_FOUND = -32000
/** The agent has no UI Automation backend. */
export const UIA_UNAVAILABLE = -32001
/** The snapshot walk used up its time budget. */
export const SNAPSHOT_TIMEOUT = -32002

/** Enumerating top-level windows is quick; more than this means the agent is stuck. */
export const LIST_WINDOWS_TIMEOUT_MS = 10_000

/**
 * The agent ends a walk at its budget and answers -32002; the client waits this much longer,
 * for sending a large tree. No answer by then means the agent itself is stuck.
 */
export const SNAPSHOT_MARGIN_MS = 10_000

/** How long the client waits for a walk on the agent's default budget. */
export const SNAPSHOT_TIMEOUT_MS = DEFAULT_SNAPSHOT_BUDGET_MS + SNAPSHOT_MARGIN_MS

/** The largest `timeoutMs` the agent takes (`docs/agent-rpc.md`). */
export const MAX_SNAPSHOT_BUDGET_MS = 600_000

export async function listWindows(agent: AgentCaller): Promise<WindowsResult> {
  let result: unknown
  try {
    result = await agent.call('listWindows', undefined, LIST_WINDOWS_TIMEOUT_MS)
  } catch (error) {
    return { ok: false, ...describeFailure(error) }
  }
  const windows = parseWindows(result)
  return windows ? { ok: true, windows } : { ok: false, reason: 'bad-response' }
}

/**
 * Captures a window. With `budgetMs` the agent may walk that long instead of its default, and
 * the client waits for it: a budget the client does not wait out would turn a slow walk into
 * "the agent did not answer" (#204). A budget outside the agent's range is not sent.
 */
export async function snapshot(
  agent: AgentCaller,
  handle: unknown,
  budgetMs?: unknown,
): Promise<SnapshotResult> {
  const budget = isBudget(budgetMs) ? budgetMs : undefined
  const params = budget === undefined ? { handle } : { handle, timeoutMs: budget }
  const wait = (budget ?? DEFAULT_SNAPSHOT_BUDGET_MS) + SNAPSHOT_MARGIN_MS
  let result: unknown
  try {
    result = await agent.call('snapshot', params, wait)
  } catch (error) {
    return { ok: false, ...describeFailure(error) }
  }
  // A newer agent is not a broken one: say which format it sends.
  if (
    isRecord(result) &&
    typeof result.version === 'string' &&
    result.version !== SNAPSHOT_VERSION
  ) {
    return { ok: false, reason: 'snapshot-version', detail: result.version }
  }
  const parsed = parseSnapshot(result)
  return parsed ? { ok: true, snapshot: parsed } : { ok: false, reason: 'bad-response' }
}

/**
 * A hit test takes milliseconds (#22: under 3.5 ms median), but UI Automation calls run one at
 * a time on the agent, so a pick pressed during a capture waits for it: this covers a walk on
 * the default budget.
 */
export const ELEMENT_FROM_POINT_TIMEOUT_MS = 10_000

/**
 * The element at `point` (physical pixels, sent as the OS gave it: the agent converts nothing).
 * A point over nothing is not an error; the answer then has nulls.
 */
export async function elementFromPoint(
  agent: AgentCaller,
  point: ScreenPoint,
): Promise<ElementFromPointResult> {
  // The agent refuses anything but integers.
  const params = { x: Math.round(point.x), y: Math.round(point.y) }
  let result: unknown
  try {
    result = await agent.call('elementFromPoint', params, ELEMENT_FROM_POINT_TIMEOUT_MS)
  } catch (error) {
    return { ok: false, ...describeFailure(error) }
  }
  const hit = parseElementHit(result)
  return hit ? { ok: true, hit } : { ok: false, reason: 'bad-response' }
}

/**
 * The `elementFromPoint` result, or null if a field has the wrong type. A field left out reads
 * as null, the value the contract gives it when there is nothing to report.
 */
export function parseElementHit(result: unknown): ElementHit | null {
  if (!isRecord(result)) return null
  const hit = {
    handle: result.handle ?? null,
    bounds: result.bounds ?? null,
    snapshotId: result.snapshotId ?? null,
    elementId: result.elementId ?? null,
    element: result.element ?? null,
  }
  if (
    !(hit.handle === null || Number.isInteger(hit.handle)) ||
    !(hit.bounds === null || isBounds(hit.bounds)) ||
    !(hit.snapshotId === null || typeof hit.snapshotId === 'string') ||
    !(hit.elementId === null || typeof hit.elementId === 'string') ||
    !(hit.element === null || isRecord(hit.element))
  ) {
    return null
  }
  return hit as ElementHit
}

/**
 * The window handle in Electron's `getNativeWindowHandle()` buffer (an HWND on Windows, in the
 * machine's little-endian order), as the agent reports handles.
 */
export function nativeHandle(bytes: Uint8Array): number {
  let value = 0
  for (let i = Math.min(bytes.length, 8) - 1; i >= 0; i--) value = value * 256 + bytes[i]
  return value
}

/** Maps an error from `AgentManager.call` to a reason the UI has a message for. */
export function describeFailure(error: unknown): { reason: AgentFailure; detail?: string } {
  if (error instanceof AgentNotConnectedError) return { reason: 'not-connected' }
  if (error instanceof AgentTimeoutError) return { reason: 'timeout' }
  if (error instanceof AgentRpcError) {
    if (error.code === UIA_UNAVAILABLE) return { reason: 'uia-unavailable' }
    if (error.code === WINDOW_NOT_FOUND) return { reason: 'window-gone' }
    // The agent's message says why the walk stopped (a blocked application or a slow window);
    // #226 will add a structured flag for the blocked case.
    if (error.code === SNAPSHOT_TIMEOUT)
      return { reason: 'snapshot-timeout', detail: error.rpcMessage }
    return { reason: 'agent-error', detail: error.rpcMessage }
  }
  return { reason: 'agent-error', detail: error instanceof Error ? error.message : String(error) }
}

/**
 * The `listWindows` result's windows, or null if it is not a window list. Each window is read
 * on its own: a null title or class name (the agent sends one when UI Automation cannot read
 * it, e.g. for an elevated process's window) becomes "", and a window that is still outside the
 * contract is left out, so one odd window cannot hide the others.
 */
export function parseWindows(result: unknown): WindowInfo[] | null {
  if (!isRecord(result) || !Array.isArray(result.windows)) return null
  const windows: WindowInfo[] = []
  for (const item of result.windows) {
    const window = parseWindow(item)
    if (window) windows.push(window)
  }
  return windows
}

function parseWindow(item: unknown): WindowInfo | null {
  if (!isRecord(item)) return null
  const title = item.title ?? ''
  const className = item.className ?? ''
  if (
    !Number.isInteger(item.handle) ||
    typeof title !== 'string' ||
    typeof className !== 'string' ||
    !Number.isInteger(item.processId) ||
    !(item.processName === null || typeof item.processName === 'string') ||
    !isBounds(item.bounds)
  ) {
    return null
  }
  return {
    handle: item.handle as number,
    title,
    className,
    processId: item.processId as number,
    processName: item.processName,
    bounds: item.bounds,
  }
}

/**
 * The `snapshot` result, or null if it is not a 0.1 snapshot whose elements form one tree.
 * Checks what the Spy relies on, not every rule of the schema: the agent's own tests
 * validate its output against `schemas/snapshot.schema.json`.
 */
export function parseSnapshot(result: unknown): Snapshot | null {
  if (
    !isRecord(result) ||
    result.version !== SNAPSHOT_VERSION ||
    typeof result.snapshotId !== 'string' ||
    !isRecord(result.capture) ||
    typeof result.capture.startedAt !== 'string' ||
    !Number.isInteger(result.capture.durationMs) ||
    !Number.isInteger(result.capture.elementCount) ||
    !isRecord(result.app) ||
    !isRecord(result.window) ||
    !Number.isInteger(result.window.handle) ||
    !Array.isArray(result.elements)
  ) {
    return null
  }
  const elements: unknown[] = result.elements
  if (!elements.every(isNode) || !buildTree(elements)) return null
  return result as unknown as Snapshot
}

function isNode(value: unknown): value is SnapshotNode {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    (value.parentId === null || typeof value.parentId === 'string') &&
    isRecord(value.element) &&
    // The two fields the Spy computes with: the highlight and the scaling.
    (value.element.bounds === undefined || isBounds(value.element.bounds)) &&
    (value.element.dpi === undefined || Number.isInteger(value.element.dpi))
  )
}

export function isBounds(value: unknown): value is Bounds {
  return (
    Array.isArray(value) &&
    value.length === 4 &&
    value.every((n) => Number.isInteger(n)) &&
    value[0] <= value[2] &&
    value[1] <= value[3]
  )
}

function isBudget(value: unknown): value is number {
  return (
    Number.isInteger(value) && (value as number) >= 1 && (value as number) <= MAX_SNAPSHOT_BUDGET_MS
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export interface Rect {
  x: number
  y: number
  width: number
  height: number
}

/**
 * Where the highlight window goes for an element at `bounds`: the agent's physical-pixel
 * rectangle converted to Electron's DIPs by `toDip`, then grown by `border` on each side so
 * the frame surrounds the element instead of covering its edge.
 */
export function frameRect(bounds: Bounds, toDip: (rect: Rect) => Rect, border: number): Rect {
  const [left, top, right, bottom] = bounds
  const dip = toDip({ x: left, y: top, width: right - left, height: bottom - top })
  return {
    x: Math.round(dip.x) - border,
    y: Math.round(dip.y) - border,
    width: Math.round(dip.width) + 2 * border,
    height: Math.round(dip.height) + 2 * border,
  }
}

/** The part of Electron's `globalShortcut` the pick hotkey needs. */
export interface ShortcutRegistry {
  register(accelerator: string, callback: () => void): boolean
  unregister(accelerator: string): void
}

/** Like TestComplete's Object Spy, so testers coming from it find the same keys. */
export const PICK_ACCELERATOR = 'CommandOrControl+Shift+A'

export function pickHotkeyLabel(platform: NodeJS.Platform): string {
  return platform === 'darwin' ? '⌘⇧A' : 'Ctrl+Shift+A'
}

/**
 * The Spy's global "pick the element under the cursor" key. Held only while the Spy is
 * shown: a global shortcut takes the key away from every other program, the one under
 * test included.
 */
export class PickHotkey {
  private active = false
  private readonly registry: ShortcutRegistry
  private readonly onPress: () => void

  constructor(registry: ShortcutRegistry, onPress: () => void) {
    this.registry = registry
    this.onPress = onPress
  }

  /** Registers or releases the key; returns whether it is now held. */
  set(enabled: boolean): boolean {
    if (enabled && !this.active) {
      // False when another program already holds the combination.
      this.active = this.registry.register(PICK_ACCELERATOR, this.onPress)
    } else if (!enabled && this.active) {
      this.registry.unregister(PICK_ACCELERATOR)
      this.active = false
    }
    return this.active
  }
}
