import { useState, type FormEvent } from 'react'
import type { ConnectionError } from '../../shared/api.ts'
import { strings } from './strings.ts'

interface Props {
  initialUrl: string
  /** Why the saved server could not be used, shown until the next attempt. */
  initialFailure?: ConnectionError
  onConnected(url: string): void
  /** Offered only when there is a working server to go back to. */
  onCancel?(): void
}

/** Server URL form: checks the server and saves the URL only when it answers. */
export default function ServerSettings({
  initialUrl,
  initialFailure,
  onConnected,
  onCancel,
}: Props) {
  const [url, setUrl] = useState(initialUrl)
  const [failure, setFailure] = useState<ConnectionError | undefined>(initialFailure)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setFailure(undefined)
    try {
      const result = await window.ayna.connectServer(url)
      if (result.ok) onConnected(result.url)
      else setFailure(result)
    } catch {
      setFailure({ ok: false, reason: 'unreachable', url })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card gate-card">
      <h2>{strings.serverTitle}</h2>
      <form className="form" onSubmit={submit}>
        <label htmlFor="server-url">{strings.serverUrlLabel}</label>
        <input
          id="server-url"
          type="text"
          inputMode="url"
          autoFocus
          spellCheck={false}
          placeholder={strings.serverUrlPlaceholder}
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          disabled={busy}
          aria-invalid={failure ? true : undefined}
          aria-describedby={failure ? 'server-error' : 'server-hint'}
        />
        {failure ? (
          <p id="server-error" className="field-error" role="alert">
            {strings.connectionErrors[failure.reason](failure.url)}
          </p>
        ) : (
          <p id="server-hint" className="hint">
            {strings.serverIntro}
          </p>
        )}
        <div className="form-actions">
          {onCancel && (
            <button type="button" onClick={onCancel} disabled={busy}>
              {strings.cancel}
            </button>
          )}
          <button type="submit" className="btn-main" disabled={busy || !url.trim()}>
            {busy ? strings.connecting : strings.connect}
          </button>
        </div>
      </form>
    </section>
  )
}
