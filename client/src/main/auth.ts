// Login and logout against the server's auth API (#60, ADR accounts-and-tokens).
// Kept free of Electron imports so plain `node --test` can use it. The session
// token never leaves the main process: the renderer gets only the `CurrentUser`.

import type { CurrentUser, RequestFailure } from '../shared/api.ts'
import { request, type Options } from './apps.ts'

export const LOGIN_PATH = '/api/auth/login'
export const LOGOUT_PATH = '/api/auth/logout'

export interface Session {
  token: string
  user: CurrentUser
}

export type LoginAnswer =
  { ok: true; session: Session } | { ok: false; reason: RequestFailure | 'wrong-credentials' }

/** Never throws. The server gives one 401 for an unknown user and a wrong password. */
export async function login(
  baseUrl: string | null,
  username: string,
  password: string,
  options: Options = {},
): Promise<LoginAnswer> {
  const init = {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }
  const answer = await request(baseUrl, LOGIN_PATH, init, { ...options, token: null })
  if (!answer.ok) {
    return answer.reason === 'unauthorized' ? { ok: false, reason: 'wrong-credentials' } : answer
  }
  const body = answer.body as Record<string, unknown> | undefined
  if (answer.status === 200 && typeof body?.token === 'string' && isUser(body.user)) {
    const { id, username: name, role } = body.user
    return { ok: true, session: { token: body.token, user: { id, username: name, role } } }
  }
  return { ok: false, reason: 'bad-response' }
}

/** Ends the session on the server. Best effort: the caller forgets the token either way. */
export async function logout(baseUrl: string | null, token: string, options: Options = {}) {
  await request(baseUrl, LOGOUT_PATH, { method: 'POST' }, { ...options, token })
}

function isUser(value: unknown): value is CurrentUser {
  if (typeof value !== 'object' || value === null) return false
  const user = value as Record<string, unknown>
  return (
    typeof user.id === 'string' &&
    typeof user.username === 'string' &&
    (user.role === 'admin' || user.role === 'tester')
  )
}
