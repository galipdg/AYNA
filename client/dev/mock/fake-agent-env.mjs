// What `npm run dev` needs in its environment to use the fake agent in this folder instead of
// the real one. Shared by `dev:mock` and `demo`.
import { delimiter, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

export const python = process.platform === 'win32' ? 'python' : 'python3'

/** The trial app's login window, the schema's own example (#12), read where it lives (#204). */
export const defaultSnapshot = resolve(here, '../../../schemas/examples/snapshot/trial-login.json')

export function fakeAgentEnv({ windows, snapshot, uia = true, slowSnapshots = false }) {
  return {
    AYNA_AGENT_PYTHON: python,
    PYTHONPATH: [here, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
    AYNA_MOCK_WINDOWS: resolve(windows),
    AYNA_MOCK_SNAPSHOT: resolve(snapshot),
    AYNA_MOCK_UIA: uia ? 'on' : 'off',
    AYNA_MOCK_SNAPSHOT_TIMEOUT: slowSnapshots ? 'on' : 'off',
  }
}
