// Which window a step plays against (#44). The agent needs a handle for every `runSteps` call,
// and a test can move between windows (a login window closes, the main window opens), so each
// step's window is looked up from its target's window title. Free of Electron imports.

import type { WindowInfo } from '../shared/api.ts'
import type { ElementDescriptor } from '../shared/element.ts'
import type { PropertySet } from '../shared/repository.ts'
import { listWindows, type AgentCaller } from './spy.ts'

/** The re-read interval, the same as the agent's own waits (`docs/agent-rpc.md`). */
export const WINDOW_POLL_MS = 250

export interface Clock {
  now(): number
  sleep(ms: number): Promise<void>
}

export const systemClock: Clock = {
  now: () => Date.now(),
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
}

/**
 * The title of the window a repository object lives in: from its "Find by" properties, else
 * its "Backup", else its last capture. Null when none says (an empty title says nothing).
 */
export function windowTitleOf(
  object: { primary: PropertySet; fallback: PropertySet },
  captured?: Partial<ElementDescriptor>,
): string | null {
  for (const title of [object.primary.windowTitle, object.fallback.windowTitle, captured?.windowTitle]) {
    if (title) return title
  }
  return null
}

export type WindowFound =
  | { handle: number }
  | { many: WindowInfo[] }
  | { none: true }
  | { failed: string }

/**
 * Waits up to `timeoutMs` for windows titled exactly `title`. One is the answer; two or more
 * are all returned, because playback never guesses which one was meant. A gone agent fails at
 * once; any other failure of `listWindows` is read again on the next round.
 */
export async function findWindow(
  agent: AgentCaller,
  title: string,
  timeoutMs: number,
  clock: Clock = systemClock,
  stopped: () => boolean = () => false,
): Promise<WindowFound> {
  const start = clock.now()
  for (;;) {
    const listed = await listWindows(agent)
    if (!listed.ok && listed.reason === 'not-connected') {
      return { failed: 'the agent is not connected' }
    }
    if (listed.ok) {
      const matching = listed.windows.filter((window) => window.title === title)
      if (matching.length === 1) return { handle: matching[0].handle }
      if (matching.length > 1) return { many: matching }
    }
    if (stopped() || clock.now() - start >= timeoutMs) return { none: true }
    await clock.sleep(WINDOW_POLL_MS)
  }
}
