import { useState, type FormEvent } from 'react'
import type { CurrentUser, LoginResult } from '../../shared/api.ts'
import { strings } from './strings.ts'

interface Props {
  url: string
  /** The previous session ended (expired, logged out elsewhere, account changed). */
  ended?: boolean
  onLoggedIn(user: CurrentUser): void
  onChangeServer(): void
}

type Failure = Extract<LoginResult, { ok: false }>['reason']

/** User name and password for the saved server (#60); the password is cleared after a failure. */
export default function Login({ url, ended, onLoggedIn, onChangeServer }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [failure, setFailure] = useState<Failure>()
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setFailure(undefined)
    try {
      const result = await window.ayna.login(username, password)
      if (result.ok) return onLoggedIn(result.user)
      setFailure(result.reason)
      setPassword('')
    } catch {
      setFailure('unreachable')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card gate-card">
      <h2>{strings.loginTitle}</h2>
      <p className="hint">
        {strings.loginIntro(url)}{' '}
        <button type="button" className="btn-quiet" onClick={onChangeServer} disabled={busy}>
          {strings.changeServer}
        </button>
      </p>
      {ended && !failure && (
        <p className="message message-warning" role="status">
          {strings.sessionEnded}
        </p>
      )}
      {failure && (
        <p id="login-error" className="message message-danger" role="alert">
          {strings.loginErrors[failure]}
        </p>
      )}
      <form className="form" onSubmit={submit}>
        <label htmlFor="login-username">{strings.usernameLabel}</label>
        <input
          id="login-username"
          type="text"
          autoFocus
          autoComplete="username"
          spellCheck={false}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="login-password">{strings.passwordLabel}</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
          aria-invalid={failure ? true : undefined}
          aria-describedby={failure ? 'login-error' : undefined}
        />
        <div className="form-actions">
          <button
            type="submit"
            className="btn-main"
            disabled={busy || !username.trim() || !password}
          >
            {busy ? strings.loggingIn : strings.logIn}
          </button>
        </div>
      </form>
    </section>
  )
}
