// Calls to the server's versions (#128), snapshot import (#15) and object repository (#25)
// APIs. Kept free of Electron imports so plain `node --test` can use it.

import type {
  AddToRepositoryResult,
  AppVersion,
  CreateVersionResult,
  FieldProblem,
  NewRepoObject,
  RepoObject,
  VersionsResult,
} from '../shared/api.ts'
import { APPS_PATH, request, type Answer, type Options } from './apps.ts'

/** A large window's snapshot takes the server longer than a plain request. */
export const IMPORT_TIMEOUT_MS = 30_000

export async function listVersions(
  baseUrl: string | null,
  appId: string,
  options: Options = {},
): Promise<VersionsResult> {
  const answer = await request(baseUrl, versionsPath(appId), { method: 'GET' }, options)
  if (!answer.ok) return answer
  if (answer.status === 200 && Array.isArray(answer.body) && answer.body.every(isVersion)) {
    return { ok: true, versions: answer.body.map(({ id, version }) => ({ id, version })) }
  }
  return { ok: false, reason: 'bad-response' }
}

export async function createVersion(
  baseUrl: string | null,
  appId: string,
  version: string,
  options: Options = {},
): Promise<CreateVersionResult> {
  const answer = await request(baseUrl, versionsPath(appId), json({ version }), options)
  if (!answer.ok) return answer
  if (answer.status === 201 && isVersion(answer.body)) {
    const { id, version: name } = answer.body
    return { ok: true, version: { id, version: name } }
  }
  const reason = ({ 400: 'invalid', 404: 'not-found', 409: 'duplicate' } as const)[answer.status]
  return reason ? { ok: false, reason, ...problem(answer) } : { ok: false, reason: 'bad-response' }
}

/**
 * Imports the capture under the version (a repeat import of the same snapshot id is a no-op
 * on the server), then creates the repository object linked to the picked element. Never
 * throws.
 */
export async function addToRepository(
  baseUrl: string | null,
  object: NewRepoObject,
  options: Options = {},
): Promise<AddToRepositoryResult> {
  const { appId, versionId, snapshot, snapshotElementId, name, primary, fallback } = object
  const imported = await request(
    baseUrl,
    `${versionsPath(appId)}/${encodeURIComponent(versionId)}/snapshots`,
    json(snapshot),
    { timeoutMs: IMPORT_TIMEOUT_MS, ...options },
  )
  if (!imported.ok) return imported
  if (imported.status !== 200 && imported.status !== 201) {
    const reason = ({ 400: 'invalid', 404: 'not-found', 409: 'snapshot-conflict' } as const)[
      imported.status
    ]
    return reason
      ? { ok: false, reason, ...problem(imported) }
      : { ok: false, reason: 'bad-response' }
  }

  const body = { name, snapshotId: snapshot.snapshotId, snapshotElementId, primary, fallback }
  const created = await request(baseUrl, `${appPath(appId)}/repo-objects`, json(body), options)
  if (!created.ok) return created
  if (created.status === 201 && isRepoObject(created.body)) {
    const { id, name: stored, primary: p, fallback: f } = created.body
    return { ok: true, object: { id, name: stored, primary: p, fallback: f } }
  }
  const reason = ({ 400: 'invalid', 404: 'not-found', 409: 'duplicate' } as const)[created.status]
  return reason ? { ok: false, reason, ...problem(created) } : { ok: false, reason: 'bad-response' }
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

function json(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  }
}

function appPath(appId: string) {
  return `${APPS_PATH}/${encodeURIComponent(appId)}`
}

function versionsPath(appId: string) {
  return `${appPath(appId)}/versions`
}

function isVersion(value: unknown): value is AppVersion {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return typeof v.id === 'string' && typeof v.version === 'string'
}

function isPropertySet(value: unknown): boolean {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isRepoObject(value: unknown): value is RepoObject {
  if (typeof value !== 'object' || value === null) return false
  const o = value as Record<string, unknown>
  return (
    typeof o.id === 'string' &&
    typeof o.name === 'string' &&
    isPropertySet(o.primary) &&
    isPropertySet(o.fallback)
  )
}

function isFieldProblem(value: unknown): value is FieldProblem {
  if (typeof value !== 'object' || value === null) return false
  const f = value as Record<string, unknown>
  return typeof f.path === 'string' && typeof f.message === 'string'
}
