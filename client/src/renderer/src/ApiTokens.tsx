import { useEffect, useState, type FormEvent } from 'react'
import type { Account, ApiToken, UsersError } from '../../shared/api.ts'
import { formatDate, strings, usersErrorText as errorText } from './strings.ts'

interface Props {
  account: Account
  onSessionEnded(): void
  onClose(): void
}

/** The CI API tokens of one account (ADR accounts-and-tokens); a new secret is shown once. */
export default function ApiTokens({ account, onSessionEnded, onClose }: Props) {
  const [tokens, setTokens] = useState<ApiToken[]>()
  const [error, setError] = useState<UsersError>()
  const [name, setName] = useState('')
  const [created, setCreated] = useState<{ name: string; secret: string }>()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    window.ayna.listTokens(account.id).then(
      (result) => {
        if (cancelled) return
        if (result.ok) setTokens(result.tokens)
        else if (result.reason === 'unauthorized') onSessionEnded()
        else setError(result)
      },
      () => !cancelled && setError({ ok: false, reason: 'unreachable' }),
    )
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account.id])

  /** Runs one call; returns its success, or null after showing the failure. */
  async function run<T extends { ok: true }>(call: () => Promise<T | UsersError>) {
    setBusy(true)
    setError(undefined)
    try {
      const result = await call()
      if (result.ok) return result
      if (result.reason === 'unauthorized') onSessionEnded()
      else setError(result)
    } catch {
      setError({ ok: false, reason: 'unreachable' })
    } finally {
      setBusy(false)
    }
    return null
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    const result = await run(() => window.ayna.createToken(account.id, name))
    if (!result) return
    setTokens((current) => [...(current ?? []), result.token])
    setCreated({ name: result.token.name, secret: result.secret })
    setName('')
  }

  async function revoke(token: ApiToken) {
    if (!(await run(() => window.ayna.revokeToken(token.id)))) return
    setTokens((current) => current?.filter((t) => t.id !== token.id))
  }

  return (
    <div className="tokens">
      <h3>{strings.tokensTitle(account.username)}</h3>
      <p className="hint">{strings.tokensIntro}</p>
      {!tokens && !error && <p className="hint">{strings.loading}</p>}
      {tokens?.length === 0 && <p className="hint">{strings.tokensEmpty}</p>}
      {tokens && tokens.length > 0 && (
        <ul className="user-list">
          {tokens.map((token) => (
            <li key={token.id} className="user-row">
              <span>
                {token.name}{' '}
                <span className="hint">{strings.createdOn(formatDate(token.createdAt))}</span>
              </span>
              <button
                type="button"
                className="btn-danger"
                onClick={() => revoke(token)}
                disabled={busy}
              >
                {strings.revokeToken}
              </button>
            </li>
          ))}
        </ul>
      )}

      {created && (
        <div className="message message-success secret" role="status">
          <p>{strings.tokenSecret(created.name)}</p>
          <input
            type="text"
            readOnly
            aria-label={strings.tokenSecret(created.name)}
            value={created.secret}
            onFocus={(event) => event.target.select()}
          />
        </div>
      )}
      {error && (
        <p className="field-error" role="alert">
          {errorText(error)}
        </p>
      )}

      {tokens && (
        <form className="form" onSubmit={create}>
          <label htmlFor={`token-name-${account.id}`}>{strings.tokenNameLabel}</label>
          <input
            id={`token-name-${account.id}`}
            type="text"
            placeholder={strings.tokenNamePlaceholder}
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={busy}
          />
          <div className="actions">
            <button type="submit" disabled={busy || !name.trim()}>
              {strings.createToken}
            </button>
            <button type="button" onClick={onClose} disabled={busy}>
              {strings.hide}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
