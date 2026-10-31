// Calls to the server's user-management API (#60, FR-39); admins only. Kept free of
// Electron imports so plain `node --test` can use it.

import type {
  Account,
  ApiToken,
  CreatedTokenResult,
  DoneResult,
  Role,
  TokensResult,
  UserResult,
  UsersError,
  UsersResult,
} from '../shared/api.ts'
import { request, type Answer, type Options } from './apps.ts'

export const USERS_PATH = '/api/users'
export const TOKENS_PATH = '/api/tokens'

/** Every account that can log in, as the server orders them. Never throws. */
export async function listUsers(
  baseUrl: string | null,
  options: Options = {},
): Promise<UsersResult> {
  const answer = await request(baseUrl, USERS_PATH, { method: 'GET' }, options)
  if (answer.ok && answer.status === 200 && Array.isArray(answer.body)) {
    if (answer.body.every(isAccount)) return { ok: true, users: answer.body.map(account) }
  }
  return failure(answer)
}

export async function createUser(
  baseUrl: string | null,
  username: string,
  password: string,
  role: Role,
  options: Options = {},
): Promise<UserResult> {
  const answer = await request(
    baseUrl,
    USERS_PATH,
    json('POST', { username, password, role }),
    options,
  )
  if (answer.ok && answer.status === 201 && isAccount(answer.body)) {
    return { ok: true, user: account(answer.body) }
  }
  return failure(answer)
}

export async function updateUser(
  baseUrl: string | null,
  id: string,
  change: { role?: Role; password?: string },
  options: Options = {},
): Promise<UserResult> {
  const body = { role: change.role, password: change.password }
  const answer = await request(baseUrl, userPath(id), json('PATCH', body), options)
  if (answer.ok && answer.status === 200 && isAccount(answer.body)) {
    return { ok: true, user: account(answer.body) }
  }
  return failure(answer)
}

export async function removeUser(
  baseUrl: string | null,
  id: string,
  options: Options = {},
): Promise<DoneResult> {
  const answer = await request(baseUrl, userPath(id), { method: 'DELETE' }, options)
  return answer.ok && answer.status === 204 ? { ok: true } : failure(answer)
}

export async function listTokens(
  baseUrl: string | null,
  userId: string,
  options: Options = {},
): Promise<TokensResult> {
  const answer = await request(baseUrl, `${userPath(userId)}/tokens`, { method: 'GET' }, options)
  if (answer.ok && answer.status === 200 && Array.isArray(answer.body)) {
    if (answer.body.every(isToken)) return { ok: true, tokens: answer.body.map(token) }
  }
  return failure(answer)
}

export async function createToken(
  baseUrl: string | null,
  userId: string,
  name: string,
  options: Options = {},
): Promise<CreatedTokenResult> {
  const path = `${userPath(userId)}/tokens`
  const answer = await request(baseUrl, path, json('POST', { name }), options)
  if (answer.ok && answer.status === 201 && isToken(answer.body)) {
    const { token: secret } = answer.body as ApiToken & { token?: unknown }
    if (typeof secret === 'string') return { ok: true, token: token(answer.body), secret }
  }
  return failure(answer)
}

export async function revokeToken(
  baseUrl: string | null,
  tokenId: string,
  options: Options = {},
): Promise<DoneResult> {
  const path = `${TOKENS_PATH}/${encodeURIComponent(tokenId)}`
  const answer = await request(baseUrl, path, { method: 'DELETE' }, options)
  return answer.ok && answer.status === 204 ? { ok: true } : failure(answer)
}

const REASONS: Record<number, UsersError['reason']> = {
  400: 'invalid',
  403: 'forbidden',
  404: 'not-found',
  409: 'conflict',
}

/** A failed request, or an answer that is not the expected success. */
function failure(answer: Answer): UsersError {
  if (!answer.ok) return answer
  const reason = REASONS[answer.status]
  if (!reason) return { ok: false, reason: 'bad-response' }
  // Problem details (RFC 9457): `detail` names what was wrong, e.g. which field (NFR-15).
  const detail = (answer.body as Record<string, unknown> | undefined)?.detail
  return typeof detail === 'string' && detail
    ? { ok: false, reason, detail }
    : { ok: false, reason }
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }
}

function userPath(id: string) {
  return `${USERS_PATH}/${encodeURIComponent(id)}`
}

function isAccount(value: unknown): value is Account {
  if (typeof value !== 'object' || value === null) return false
  const user = value as Record<string, unknown>
  return (
    typeof user.id === 'string' &&
    typeof user.username === 'string' &&
    (user.role === 'admin' || user.role === 'tester') &&
    typeof user.createdAt === 'string'
  )
}

function isToken(value: unknown): value is ApiToken {
  if (typeof value !== 'object' || value === null) return false
  const t = value as Record<string, unknown>
  return typeof t.id === 'string' && typeof t.name === 'string' && typeof t.createdAt === 'string'
}

// Copy only the known fields, so nothing else the server sends reaches the renderer.
function account({ id, username, role, createdAt }: Account): Account {
  return { id, username, role, createdAt }
}

function token({ id, name, createdAt }: ApiToken): ApiToken {
  return { id, name, createdAt }
}
