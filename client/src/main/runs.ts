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
import { stepOutcomeFrom, type StepOutcome } from '../shared/liveRun.ts'
import type { StepDocument } from '../shared/steps.ts'
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
export function toRun(value: unknown): RunSummary | null {
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

/** A run just created, with the copy of its steps that its `stepIndex`es point into. */
export interface CreatedRun {
  run: RunSummary
  document: StepDocument
}

/**
 * What a write to a run came to, as the outbox acts on it: `retry` later (the server is away),
 * wait for a sign-in, or give the run up because the server will never take it (`gone`: the
 * run or its test was deleted; `conflict`: another body for the step, a finished run, or a body
 * the server refuses).
 */
export type WriteAnswer = 'stored' | 'retry' | 'unauthorized' | 'gone' | 'conflict'

/** Starts a run of the test's saved steps on `appVersionId` (#44). Never throws. */
export async function createRun(
  baseUrl: string | null,
  testId: string,
  appVersionId: string,
  options: Options = {},
): Promise<{ ok: true; created: CreatedRun } | RunsError> {
  const init = {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ testId, appVersionId }),
  }
  const answer = await request(baseUrl, '/api/runs', init, options)
  if (!answer.ok) return answer
  if (answer.status === 201) {
    const run = toRun(answer.body)
    const document = (answer.body as Record<string, unknown>).document
    if (run && isDocument(document)) return { ok: true, created: { run, document } }
  }
  return failure(answer)
}

/** One run with its stored results, in step order. Never throws. */
export async function getRun(
  baseUrl: string | null,
  runId: string,
  options: Options = {},
): Promise<{ ok: true; run: RunSummary; outcomes: StepOutcome[] } | RunsError> {
  const path = `/api/runs/${encodeURIComponent(runId)}`
  const answer = await request(baseUrl, path, { method: 'GET' }, options)
  if (!answer.ok) return answer
  if (answer.status === 200) {
    const run = toRun(answer.body)
    const results = (answer.body as Record<string, unknown>).results
    const outcomes = Array.isArray(results) ? results.map(stepOutcomeFrom) : null
    if (run && outcomes && outcomes.every((outcome) => outcome !== null)) {
      return { ok: true, run, outcomes: outcomes.sort((a, b) => a.stepIndex - b.stepIndex) }
    }
  }
  return failure(answer)
}

/** The test's runs that are still going, newest first. Never throws. */
export async function listRunningRuns(
  baseUrl: string | null,
  testId: string,
  options: Options = {},
): Promise<RunsResult> {
  const path = `/api/tests/${encodeURIComponent(testId)}/runs?status=running`
  const answer = await request(baseUrl, path, { method: 'GET' }, options)
  if (!answer.ok) return answer
  if (answer.status === 200 && Array.isArray(answer.body)) {
    const runs = answer.body.map(toRun)
    if (runs.every((run) => run !== null)) return { ok: true, runs }
  }
  return failure(answer)
}

/** Stores one step's result; `body` is the result as the agent sent it, with the run's ids. */
export async function putResult(
  baseUrl: string | null,
  runId: string,
  body: Record<string, unknown>,
  options: Options = {},
): Promise<WriteAnswer> {
  const path = `/api/runs/${encodeURIComponent(runId)}/results/${String(body.stepIndex)}`
  const init = { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }
  return writeAnswer(await request(baseUrl, path, init, options))
}

/** Finishes the run with `status`; the server checks it against the stored results. */
export async function finishRun(
  baseUrl: string | null,
  runId: string,
  status: RunStatus,
  options: Options = {},
): Promise<WriteAnswer> {
  const path = `/api/runs/${encodeURIComponent(runId)}/finish`
  const init = { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ status }) }
  return writeAnswer(await request(baseUrl, path, init, options))
}

function writeAnswer(answer: Answer): WriteAnswer {
  if (!answer.ok) return answer.reason === 'unauthorized' ? 'unauthorized' : 'retry'
  if (answer.status === 200 || answer.status === 201) return 'stored'
  if (answer.status === 404) return 'gone'
  // A body the server refuses now it will refuse on every retry too.
  if (answer.status === 400 || answer.status === 409) return 'conflict'
  return 'retry'
}

function isDocument(value: unknown): value is StepDocument {
  if (typeof value !== 'object' || value === null) return false
  const d = value as Record<string, unknown>
  return typeof d.version === 'string' && Array.isArray(d.steps)
}
