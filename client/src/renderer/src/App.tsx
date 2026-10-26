import { useEffect, useState } from 'react'
import type { AppInfo, ConnectionError } from '../../shared/api.ts'
import ServerSettings from './ServerSettings.tsx'
import { strings } from './strings.ts'

type Connection =
  | { phase: 'loading'; url?: string }
  | { phase: 'settings'; url: string; failure?: ConnectionError; previous?: string }
  | { phase: 'connected'; url: string }

export default function App() {
  const [info, setInfo] = useState<AppInfo | null>(null)
  const [error, setError] = useState(false)
  const [connection, setConnection] = useState<Connection>({ phase: 'loading' })

  useEffect(() => {
    window.ayna.getAppInfo().then(setInfo, () => setError(true))
  }, [])

  // First run shows the settings screen; later runs check the saved server first.
  useEffect(() => {
    let cancelled = false
    async function start() {
      const { serverUrl } = await window.ayna.getSettings()
      if (cancelled) return
      if (!serverUrl) return setConnection({ phase: 'settings', url: '' })
      setConnection({ phase: 'loading', url: serverUrl })
      const result = await window.ayna.checkServer(serverUrl)
      if (cancelled) return
      setConnection(
        result.ok
          ? { phase: 'connected', url: result.url }
          : { phase: 'settings', url: serverUrl, failure: result },
      )
    }
    start().catch(() => !cancelled && setError(true))
    return () => {
      cancelled = true
    }
  }, [])

  const previous = connection.phase === 'settings' ? connection.previous : undefined

  return (
    <main className="app">
      <h1>{strings.appName}</h1>
      <p className="tagline">{strings.tagline}</p>

      {connection.phase === 'loading' && !error && (
        <p>{connection.url ? strings.checkingSaved(connection.url) : strings.loading}</p>
      )}
      {connection.phase === 'settings' && (
        <ServerSettings
          initialUrl={connection.url}
          initialFailure={connection.failure}
          onConnected={(url) => setConnection({ phase: 'connected', url })}
          onCancel={
            previous ? () => setConnection({ phase: 'connected', url: previous }) : undefined
          }
        />
      )}
      {connection.phase === 'connected' && (
        <section className="card connected">
          <p className="ok">{strings.connectedTo(connection.url)}</p>
          <button
            type="button"
            onClick={() =>
              setConnection({ phase: 'settings', url: connection.url, previous: connection.url })
            }
          >
            {strings.changeServer}
          </button>
        </section>
      )}

      <section className="card">
        <h2>{strings.versionsTitle}</h2>
        {error && <p className="error">{strings.bridgeError}</p>}
        {!error && !info && <p>{strings.loading}</p>}
        {info && (
          <dl>
            <dt>App</dt>
            <dd>
              {info.name} {info.version}
            </dd>
            <dt>Electron</dt>
            <dd>{info.electron}</dd>
            <dt>Chromium</dt>
            <dd>{info.chrome}</dd>
            <dt>Node</dt>
            <dd>{info.node}</dd>
            <dt>Platform</dt>
            <dd>{info.platform}</dd>
          </dl>
        )}
      </section>
    </main>
  )
}
