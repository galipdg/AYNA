// Calls to the server's run history (#68) and run report (#59). Kept free of Electron imports
// so plain `node --test` can use it; `index.ts` shows and saves the report.

import {
  RUN_STATUSES,
  type RunFilter,
  type RunsError,
  type RunsResult,
  type RunStatus,
  type RunSummary,
} from '../shared/api.ts'
import type { Language } from '../shared/language.ts'
import { APPS_PATH, request, type Answer, type Options } from './apps.ts'

/** A 50-step report with full-screen screenshots is about 15 MB (#59); give it time. */
export const REPORT_TIMEOUT_MS = 60_000

/** The application's runs, newest first, narrowed by `filter`. Never throws. */
export async function listRuns(
  baseUrl: string | null,
  appId: string,
  filter: RunFilter,
  options: Options = {},
): Promise<RunsResult> {
  const query = new URLSearchParams()
  if (filter.testId) query.set('testId', filter.testId)
  if (filter.status) query.set('status', filter.status)
  const path = `${APPS_PATH}/${encodeURIComponent(appId)}/runs${query.size ? `?${query}` : ''}`
  const answer = await request(baseUrl, path, { method: 'GET' }, options)
  if (!answer.ok) return answer
  if (answer.status === 200 && Array.isArray(answer.body)) {
    const runs = answer.body.map(toRun)
    if (runs.every((run) => run !== null)) return { ok: true, runs }
  }
  return failure(answer)
}

export type ReportAnswer = { ok: true; html: string } | RunsError

/**
 * The run's report as the server renders it, in `language`. Read as text, since `request`
 * reads JSON; error statuses still answer with a problem body. Never throws.
 */
export async function fetchReport(
  baseUrl: string | null,
  runId: string,
  language: Language,
  { fetch = globalThis.fetch, timeoutMs = REPORT_TIMEOUT_MS, token }: Options = {},
): Promise<ReportAnswer> {
  if (!baseUrl) return { ok: false, reason: 'no-server' }
  const path = `/api/runs/${encodeURIComponent(runId)}/report.html?lang=${language}`
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      headers: { accept: 'text/html', ...(token ? { authorization: `Bearer ${token}` } : {}) },
      signal: AbortSignal.timeout(timeoutMs),
    })
    if (response.status === 401) return { ok: false, reason: 'unauthorized' }
    const type = response.headers.get('content-type') ?? ''
    if (response.status === 200 && type.startsWith('text/html')) {
      return { ok: true, html: await response.text() }
    }
    let body: unknown
    try {
      body = await response.json()
    } catch {
      // Judged by the status alone.
    }
    return failure({ ok: true, status: response.status, body })
  } catch (error) {
    const timeout = error instanceof Error && error.name === 'TimeoutError'
    return { ok: false, reason: timeout ? 'timeout' : 'unreachable' }
  }
}

/**
 * A file name for a saved report from a name the renderer suggests: no folders, no characters
 * Windows refuses, none of its reserved device names (`CON`, `NUL`, `COM1`…), at most 120
 * characters, always `.html`.
 */
export function reportFileName(suggested: string): string {
  const name = suggested
    .replace(/\.html$/i, '')
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/./gu, (c) => (c.charCodeAt(0) < 32 ? '-' : c))
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^\.+/, '')
    .slice(0, 120)
    .trim()
  // Windows refuses these names with any extension.
  const reserved = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$/i.test(name)
  return `${reserved ? `ayna-run ${name}` : name || 'ayna-run'}.html`
}

function failure(answer: Extract<Answer, { ok: true }>): RunsError {
  const reason = ({ 400: 'invalid', 404: 'not-found' } as const)[answer.status as 400 | 404]
  if (!reason) return { ok: false, reason: 'bad-response' }
  const body = (answer.body ?? {}) as Record<string, unknown>
  return typeof body.detail === 'string' && body.detail
    ? { ok: false, reason, detail: body.detail }
    : { ok: false, reason }
}

/** A run as the server's `RunSummary` sends it, or null if it is not one. */
function toRun(value: unknown): RunSummary | null {
  if (typeof value !== 'object' || value === null) return null
  const r = value as Record<string, unknown>
  const startedBy = (r.startedBy ?? {}) as Record<string, unknown>
  if (
    typeof r.id !== 'string' ||
    typeof r.testId !== 'string' ||
    typeof r.appVersionId !== 'string' ||
    !RUN_STATUSES.includes(r.status as RunStatus) ||
    !Number.isInteger(r.stepCount) ||
    typeof r.startedAt !== 'string' ||
    typeof startedBy.id !== 'string'
  ) {
    return null
  }
  return {
    id: r.id,
    testId: r.testId,
    appVersionId: r.appVersionId,
    status: r.status as RunStatus,
    stepCount: r.stepCount as number,
    startedBy: typeof startedBy.username === 'string' ? startedBy.username : startedBy.id,
    startedAt: r.startedAt,
    finishedAt: typeof r.finishedAt === 'string' ? r.finishedAt : null,
    durationMs: typeof r.durationMs === 'number' ? r.durationMs : null,
  }
}
