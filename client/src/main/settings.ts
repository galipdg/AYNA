// Per-machine settings in one JSON file under Electron's user data folder.
// Kept free of Electron imports; the main process passes in the file path.

import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import type { Settings } from '../shared/api.ts'

export const SETTINGS_FILE = 'settings.json'

const DEFAULTS: Settings = { serverUrl: null, applicationId: null }

/** Reads the settings; a missing, unreadable or malformed file yields the defaults. */
export async function loadSettings(file: string): Promise<Settings> {
  let data: unknown
  try {
    data = JSON.parse(await readFile(file, 'utf8'))
  } catch {
    return { ...DEFAULTS }
  }
  const stored = typeof data === 'object' && data !== null ? (data as Record<string, unknown>) : {}
  return {
    serverUrl: typeof stored.serverUrl === 'string' ? stored.serverUrl : DEFAULTS.serverUrl,
    applicationId:
      typeof stored.applicationId === 'string' ? stored.applicationId : DEFAULTS.applicationId,
  }
}

/** The settings after connecting to `serverUrl`: application ids belong to one server. */
export function withServer(settings: Settings, serverUrl: string): Settings {
  return {
    serverUrl,
    applicationId: settings.serverUrl === serverUrl ? settings.applicationId : null,
  }
}

/** Writes the settings atomically (temp file + rename), so a crash never leaves half a file. */
export async function saveSettings(file: string, settings: Settings): Promise<void> {
  await mkdir(dirname(file), { recursive: true })
  const temp = `${file}.tmp`
  await writeFile(temp, `${JSON.stringify(settings, null, 2)}\n`, 'utf8')
  await rename(temp, file)
}
