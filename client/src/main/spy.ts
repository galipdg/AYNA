// The Spy's calls to the local agent, turned into plain results for the renderer.
// Free of Electron imports so `node --test` can run it against a stub agent.

import type { AgentFailure, Bounds, WindowInfo, WindowsResult } from '../shared/api.ts'
import { AgentNotConnectedError, AgentRpcError, AgentTimeoutError } from './agent.ts'

/** The part of `AgentManager` the Spy needs. */
export interface AgentCaller {
  call(method: string, params?: Record<string, unknown>, timeoutMs?: number): Promise<unknown>
}

/** `-32001` in `docs/agent-rpc.md`: the agent has no UI Automation backend. */
export const UIA_UNAVAILABLE = -32001

/** Enumerating top-level windows is quick; more than this means the agent is stuck. */
export const LIST_WINDOWS_TIMEOUT_MS = 10_000

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

/** Maps an error from `AgentManager.call` to a reason the UI has a message for. */
export function describeFailure(error: unknown): { reason: AgentFailure; detail?: string } {
  if (error instanceof AgentNotConnectedError) return { reason: 'not-connected' }
  if (error instanceof AgentTimeoutError) return { reason: 'timeout' }
  if (error instanceof AgentRpcError) {
    if (error.code === UIA_UNAVAILABLE) return { reason: 'uia-unavailable' }
    return { reason: 'agent-error', detail: error.rpcMessage }
  }
  return { reason: 'agent-error', detail: error instanceof Error ? error.message : String(error) }
}

/** The `listWindows` result's windows, or null if it does not match the contract. */
export function parseWindows(result: unknown): WindowInfo[] | null {
  if (!isRecord(result) || !Array.isArray(result.windows)) return null
  const windows: WindowInfo[] = []
  for (const item of result.windows) {
    if (
      !isRecord(item) ||
      !Number.isInteger(item.handle) ||
      typeof item.title !== 'string' ||
      typeof item.className !== 'string' ||
      !Number.isInteger(item.processId) ||
      !(item.processName === null || typeof item.processName === 'string') ||
      !isBounds(item.bounds)
    ) {
      return null
    }
    windows.push({
      handle: item.handle as number,
      title: item.title,
      className: item.className,
      processId: item.processId as number,
      processName: item.processName,
      bounds: item.bounds,
    })
  }
  return windows
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
