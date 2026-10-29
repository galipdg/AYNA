// Calls to the server's applications API (#128). Kept free of Electron imports so
// plain `node --test` can use it; the main process passes in the real `fetch`.

import type {
  Application,
  ApplicationsResult,
  CreateApplicationResult,
  RequestFailure,
} from '../shared/api.ts'

export const APPS_PATH = '/api/apps'
export const REQUEST_TIMEOUT_MS = 5000

interface Options {
  fetch?: typeof globalThis.fetch
  timeoutMs?: number
}

/** Lists the applications on the server at `baseUrl`. Never throws. */
export async function listApplications(
  baseUrl: string | null,
  options: Options = {},
): Promise<ApplicationsResult> {
  const answer = await request(baseUrl, { method: 'GET' }, options)
  if (!answer.ok) return answer
  const { status, body } = answer
  if (status === 200 && Array.isArray(body) && body.every(isApplication)) {
    return { ok: true, apps: body }
  }
  return { ok: false, reason: 'bad-response' }
}

/** Creates an application on the server at `baseUrl`. Never throws. */
export async function createApplication(
  baseUrl: string | null,
  name: string,
  technology: string,
  options: Options = {},
): Promise<CreateApplicationResult> {
  const init = {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ name, technology }),
  }
  const answer = await request(baseUrl, init, options)
  if (!answer.ok) return answer
  const { status, body } = answer
  if (status === 201 && isApplication(body)) return { ok: true, app: body }
  if (status === 409) return { ok: false, reason: 'duplicate' }
  if (status === 400) return { ok: false, reason: 'invalid' }
  return { ok: false, reason: 'bad-response' }
}

type Answer = { ok: true; status: number; body: unknown } | { ok: false; reason: RequestFailure }

async function request(
  baseUrl: string | null,
  init: RequestInit,
  { fetch = globalThis.fetch, timeoutMs = REQUEST_TIMEOUT_MS }: Options,
): Promise<Answer> {
  if (!baseUrl) return { ok: false, reason: 'no-server' }
  let response: Response
  try {
    response = await fetch(`${baseUrl}${APPS_PATH}`, {
      ...init,
      headers: { accept: 'application/json', ...init.headers },
      signal: AbortSignal.timeout(timeoutMs),
    })
  } catch (error) {
    return { ok: false, reason: isTimeout(error) ? 'timeout' : 'unreachable' }
  }
  let body: unknown
  try {
    body = await response.json()
  } catch (error) {
    // The timeout also covers reading the body. A body that is not JSON is left
    // undefined: error statuses are judged by their code alone.
    if (isTimeout(error)) return { ok: false, reason: 'timeout' }
  }
  return { ok: true, status: response.status, body }
}

function isApplication(value: unknown): value is Application {
  if (typeof value !== 'object' || value === null) return false
  const app = value as Record<string, unknown>
  return (
    typeof app.id === 'string' && typeof app.name === 'string' && typeof app.technology === 'string'
  )
}

function isTimeout(error: unknown): boolean {
  return error instanceof Error && error.name === 'TimeoutError'
}
