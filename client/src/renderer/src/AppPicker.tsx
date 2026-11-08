import { useEffect, useState, type FormEvent } from 'react'
import type { Application, CreateApplicationResult, RequestFailure } from '../../shared/api.ts'
import { strings } from './strings.ts'

interface Props {
  /** The chosen application, highlighted in the list. */
  selectedId?: string
  /** The saved application was not found on the server. */
  missing?: boolean
  onChosen(app: Application): void
  /** The server answered 401: the session is gone, so the login screen takes over. */
  onSessionEnded(): void
  /** Offered only when there is a chosen application to go back to. */
  onCancel?(): void
}

type List =
  | { state: 'loading' }
  | { state: 'loaded'; apps: Application[] }
  | { state: 'failed'; reason: RequestFailure }

type CreateFailure = Extract<CreateApplicationResult, { ok: false }>['reason']

async function fetchList(): Promise<List> {
  try {
    const result = await window.ayna.listApplications()
    return result.ok
      ? { state: 'loaded', apps: result.apps }
      : { state: 'failed', reason: result.reason }
  } catch {
    return { state: 'failed', reason: 'unreachable' }
  }
}

/** Lists the server's applications; choosing one (or adding a new one) saves it for this machine. */
export default function AppPicker({
  selectedId,
  missing,
  onChosen,
  onSessionEnded,
  onCancel,
}: Props) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [name, setName] = useState('')
  const [technology, setTechnology] = useState('')
  const [createFailure, setCreateFailure] = useState<CreateFailure>()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchList().then((next) => !cancelled && show(next))
    return () => {
      cancelled = true
    }
    // `show` only reads props that do not change while the picker is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function show(next: List) {
    if (next.state === 'failed' && next.reason === 'unauthorized') onSessionEnded()
    else setList(next)
  }

  function retry() {
    setList({ state: 'loading' })
    fetchList().then(show)
  }

  async function choose(app: Application) {
    setBusy(true)
    try {
      await window.ayna.chooseApplication(app.id)
      onChosen(app)
    } finally {
      setBusy(false)
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setCreateFailure(undefined)
    try {
      const result = await window.ayna.createApplication(name, technology)
      if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
      if (!result.ok) return setCreateFailure(result.reason)
      await window.ayna.chooseApplication(result.app.id)
      onChosen(result.app)
    } catch {
      setCreateFailure('unreachable')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>{strings.appsTitle}</h2>
      <p>{strings.appsIntro}</p>
      {missing && (
        <p className="error" role="alert">
          {strings.appsMissing}
        </p>
      )}

      {list.state === 'loading' && <p>{strings.loading}</p>}
      {list.state === 'failed' && (
        <div className="actions">
          <p className="error" role="alert">
            {strings.requestErrors[list.reason]}
          </p>
          <button type="button" onClick={retry}>
            {strings.appsRetry}
          </button>
        </div>
      )}
      {list.state === 'loaded' && list.apps.length === 0 && <p>{strings.appsEmpty}</p>}
      {list.state === 'loaded' && list.apps.length > 0 && (
        <ul className="app-list">
          {list.apps.map((app) => (
            <li key={app.id}>
              <button
                type="button"
                className={app.id === selectedId ? 'selected' : undefined}
                aria-pressed={app.id === selectedId}
                onClick={() => choose(app)}
                disabled={busy}
              >
                <span>{app.name}</span>
                <span className="technology">{app.technology}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <h3>{strings.newAppTitle}</h3>
      <form className="app-form" onSubmit={create}>
        <label htmlFor="app-name">{strings.appNameLabel}</label>
        <input
          id="app-name"
          type="text"
          placeholder={strings.appNamePlaceholder}
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={busy}
        />
        <label htmlFor="app-technology">{strings.appTechnologyLabel}</label>
        <input
          id="app-technology"
          type="text"
          placeholder={strings.appTechnologyPlaceholder}
          value={technology}
          onChange={(event) => setTechnology(event.target.value)}
          disabled={busy}
        />
        <div className="actions">
          <button type="submit" disabled={busy || !name.trim() || !technology.trim()}>
            {busy ? strings.creatingApp : strings.createApp}
          </button>
          {onCancel && (
            <button type="button" onClick={onCancel} disabled={busy}>
              {strings.cancel}
            </button>
          )}
        </div>
      </form>
      {createFailure && (
        <p className="error" role="alert">
          {strings.requestErrors[createFailure]}
        </p>
      )}
    </section>
  )
}
