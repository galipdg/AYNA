// Calls to the server's tests API (#39) and the step schema check of the editor (#38). Kept
// free of Electron imports so plain `node --test` can use it.
//
// The check runs here, not in the renderer: Ajv compiles a schema into a function with
// `new Function`, which the renderer's Content-Security-Policy (`script-src 'self'`) forbids.

import Ajv2020 from 'ajv/dist/2020.js'
import stepSchema from '../../../schemas/step.schema.json' with { type: 'json' }
import type {
  FieldProblem,
  TestCase,
  TestDeleteResult,
  TestError,
  TestResult,
  TestsResult,
  TestSummary,
} from '../shared/api.ts'
import { schemaProblems, type StepDocument, type StepProblem } from '../shared/steps.ts'
import { APPS_PATH, request, type Answer, type Options } from './apps.ts'

const validate = new Ajv2020({ allErrors: true, strict: false }).compile(stepSchema)

/** The step schema's verdict on `document`: one problem per step and reason, none when valid. */
export function validateSteps(document: unknown): StepProblem[] {
  return validate(document) ? [] : schemaProblems(validate.errors ?? [])
}

export async function listTests(
  baseUrl: string | null,
  appId: string,
  options: Options = {},
): Promise<TestsResult> {
  const answer = await request(baseUrl, testsPath(appId), { method: 'GET' }, options)
  if (!answer.ok) return answer
  if (answer.status === 200 && Array.isArray(answer.body) && answer.body.every(isSummary)) {
    return {
      ok: true,
      tests: answer.body.map(({ id, name, stepCount }) => ({ id, name, stepCount })),
    }
  }
  return failure(answer)
}

export async function createTest(
  baseUrl: string | null,
  appId: string,
  name: string,
  options: Options = {},
): Promise<TestResult> {
  const answer = await request(baseUrl, testsPath(appId), json({ name }), options)
  return answer.ok ? test(answer, 201) : answer
}

export async function getTest(
  baseUrl: string | null,
  id: string,
  options: Options = {},
): Promise<TestResult> {
  const answer = await request(baseUrl, testPath(id), { method: 'GET' }, options)
  return answer.ok ? test(answer) : answer
}

export async function renameTest(
  baseUrl: string | null,
  id: string,
  name: string,
  options: Options = {},
): Promise<TestResult> {
  const answer = await request(baseUrl, testPath(id), json({ name }, 'PATCH'), options)
  return answer.ok ? test(answer) : answer
}

export async function deleteTest(
  baseUrl: string | null,
  id: string,
  options: Options = {},
): Promise<TestDeleteResult> {
  const answer = await request(baseUrl, testPath(id), { method: 'DELETE' }, options)
  if (!answer.ok) return answer
  return answer.status === 204 ? { ok: true } : failure(answer)
}

/** Replaces the test's steps; steps with an `id` keep it, the others get new ones. */
export async function saveSteps(
  baseUrl: string | null,
  id: string,
  document: StepDocument,
  options: Options = {},
): Promise<TestResult> {
  const answer = await request(baseUrl, `${testPath(id)}/steps`, json(document, 'PUT'), options)
  return answer.ok ? test(answer) : answer
}

/** A test body with the expected status, or the failure its status means. */
function test(answer: Extract<Answer, { ok: true }>, expected = 200): TestResult {
  if (answer.status === expected && isTest(answer.body)) {
    const { id, name, document, updatedBy, updatedAt } = answer.body
    const result: TestCase = { id, name, document, updatedAt }
    if (typeof updatedBy?.username === 'string') result.updatedBy = updatedBy.username
    return { ok: true, test: result }
  }
  return failure(answer)
}

function failure(answer: Extract<Answer, { ok: true }>): TestError {
  const reason = ({ 400: 'invalid', 404: 'not-found', 409: 'duplicate' } as const)[
    answer.status as 400 | 404 | 409
  ]
  return reason ? { ok: false, reason, ...problem(answer) } : { ok: false, reason: 'bad-response' }
}

/** `detail` and the field `errors` of a problem-details body (RFC 9457), when present. */
function problem(answer: Extract<Answer, { ok: true }>): {
  detail?: string
  fields?: FieldProblem[]
} {
  const body = (answer.body ?? {}) as Record<string, unknown>
  const result: { detail?: string; fields?: FieldProblem[] } = {}
  if (typeof body.detail === 'string' && body.detail) result.detail = body.detail
  if (Array.isArray(body.errors)) {
    const fields = body.errors
      .filter(isFieldProblem)
      .map(({ path, message }) => ({ path, message }))
    if (fields.length) result.fields = fields
  }
  return result
}

function json(body: unknown, method = 'POST'): RequestInit {
  return {
    method,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  }
}

function testsPath(appId: string) {
  return `${APPS_PATH}/${encodeURIComponent(appId)}/tests`
}

function testPath(id: string) {
  return `/api/tests/${encodeURIComponent(id)}`
}

function isFieldProblem(value: unknown): value is FieldProblem {
  if (typeof value !== 'object' || value === null) return false
  const f = value as Record<string, unknown>
  return typeof f.path === 'string' && typeof f.message === 'string'
}

function isSummary(value: unknown): value is TestSummary {
  if (typeof value !== 'object' || value === null) return false
  const t = value as Record<string, unknown>
  return typeof t.id === 'string' && typeof t.name === 'string' && Number.isInteger(t.stepCount)
}

/** A stored test; its document passed the server's schema check, so only its shape is read. */
function isTest(value: unknown): value is Omit<TestCase, 'updatedBy'> & {
  updatedBy?: { username?: unknown } | null
} {
  if (typeof value !== 'object' || value === null) return false
  const t = value as Record<string, unknown>
  const document = t.document as Record<string, unknown> | null
  return (
    typeof t.id === 'string' &&
    typeof t.name === 'string' &&
    typeof t.updatedAt === 'string' &&
    typeof document === 'object' &&
    document !== null &&
    Array.isArray(document.steps)
  )
}
