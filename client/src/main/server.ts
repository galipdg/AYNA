// Server URL handling and the connection check. Kept free of Electron imports so
// plain `node --test` can use it; the main process passes in the real `fetch`.

import { CHECK_TIMEOUT_MS, type ConnectionResult } from '../shared/api.ts'

export const HEALTH_PATH = '/api/health'
export { CHECK_TIMEOUT_MS }

/**
 * Turns what the user typed into a base URL, or null if it cannot be one.
 * A missing scheme means `http://`; trailing slashes go; only http(s) without
 * credentials, query or fragment is accepted.
 */
export function normalizeServerUrl(input: string): string | null {
  const text = input.trim()
  if (!text) return null
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(text) ? text : `http://${text}`
  let url: URL
  try {
    url = new URL(withScheme)
  } catch {
    return null
  }
  if (!['http:', 'https:'].includes(url.protocol)) return null
  if (!url.hostname || url.username || url.password || url.search || url.hash) return null
  return `${url.origin}${url.pathname.replace(/\/+$/, '')}`
}

/**
 * Asks the server's health endpoint whether it is an AYNA server that can reach
 * its database. Never throws: every failure maps to a `ConnectionFailure`.
 */
export async function checkServer(
  input: string,
  { fetch = globalThis.fetch, timeoutMs = CHECK_TIMEOUT_MS } = {},
): Promise<ConnectionResult> {
  const url = normalizeServerUrl(input)
  if (!url) return { ok: false, reason: 'invalid-url' }

  let response: Response
  try {
    response = await fetch(`${url}${HEALTH_PATH}`, {
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(timeoutMs),
    })
  } catch (error) {
    return { ok: false, reason: isTimeout(error) ? 'timeout' : 'unreachable', url }
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (error) {
    // The timeout also covers reading the body; anything else means it was not JSON.
    return { ok: false, reason: isTimeout(error) ? 'timeout' : 'not-ayna', url }
  }
  const status = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {}
  if (response.ok && status.status === 'UP') return { ok: true, url }
  if (response.status === 503 && status.db === 'DOWN') return { ok: false, reason: 'db-down', url }
  return { ok: false, reason: 'not-ayna', url }
}

function isTimeout(error: unknown): boolean {
  return error instanceof Error && error.name === 'TimeoutError'
}
