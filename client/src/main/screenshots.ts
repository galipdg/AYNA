// Step screenshots after a run from the editor (#261, ADR run-screenshots, agent-rpc 1.2).
// The agent writes each step's PNG and sends its path (`screenshotPath`); this module takes the
// file away from the agent at once and keeps it in the client's own folder until the outbox has
// uploaded it. Free of Electron imports.
//
// Why at once: the client plays one `runSteps` call per step (#44), and the agent names each
// image by its index *within the call*, so every step of a run writes the same
// `run-<runId>/step-0000.png`. The next step would overwrite the image before a slow (or away)
// server got it.

import { copyFile, mkdir, rm, unlink } from 'node:fs/promises'
import { basename, dirname, join } from 'node:path'

/** The agent's folder for all runs' images, under the system temp folder (`SCREENSHOT_ROOT`). */
export const AGENT_SCREENSHOT_ROOT = 'ayna-screenshots'

/** The client's folder for images not uploaded yet, in the user's data folder. */
export const OWN_SCREENSHOT_DIR = 'run-screenshots'

export interface ScreenshotKeeper {
  /** Takes the agent's PNG for a step; the client's copy's path, or null if there is none. */
  keep(runId: string, stepIndex: number, agentPath: string): Promise<string | null>
  /** The run has ended: removes the agent's folders it wrote for this run. */
  release(runId: string): Promise<void>
}

/** Where a run's images wait for upload; one folder per run. */
export function ownRunDir(root: string, runId: string): string {
  return join(root, safeName(runId))
}

/**
 * True for a folder the agent made for a run: `…/ayna-screenshots/run-…`. The path comes from
 * another process, so nothing else is ever removed on its word.
 */
export function isAgentRunDir(dir: string): boolean {
  return (
    basename(dirname(dir)) === AGENT_SCREENSHOT_ROOT && /^run-[A-Za-z0-9._-]+$/.test(basename(dir))
  )
}

export function screenshotKeeper(
  root: string,
  log: (line: string) => void = console.log,
): ScreenshotKeeper {
  const agentDirs = new Map<string, Set<string>>()
  return {
    async keep(runId, stepIndex, agentPath) {
      const dir = dirname(agentPath)
      if (!isAgentRunDir(dir) || !agentPath.toLowerCase().endsWith('.png')) {
        log(`[screenshots] ignored ${agentPath}: not in the agent's screenshot folder`)
        return null
      }
      agentDirs.set(runId, (agentDirs.get(runId) ?? new Set()).add(dir))
      const target = join(ownRunDir(root, runId), `step-${String(stepIndex).padStart(4, '0')}.png`)
      try {
        await mkdir(dirname(target), { recursive: true })
        // A copy, not a rename: the temp folder and the data folder may be on different drives.
        await copyFile(agentPath, target)
      } catch (error) {
        // A missing image is normal (#54: a capture that fails is skipped); the step still counts.
        log(`[screenshots] step ${stepIndex} of run ${runId}: ${message(error)}`)
        return null
      } finally {
        await unlink(agentPath).catch(() => undefined)
      }
      return target
    },
    async release(runId) {
      for (const dir of agentDirs.get(runId) ?? []) {
        await rm(dir, { recursive: true, force: true }).catch((error) =>
          log(`[screenshots] could not remove ${dir}: ${message(error)}`),
        )
      }
      agentDirs.delete(runId)
    },
  }
}

/** Removes a run's own copies once the outbox is done with the run, delivered or not. */
export async function removeOwnRunDir(root: string, runId: string): Promise<void> {
  await rm(ownRunDir(root, runId), { recursive: true, force: true })
}

function safeName(runId: string): string {
  return runId.replace(/[^A-Za-z0-9._-]/g, '_')
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
