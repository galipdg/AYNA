import { useEffect, useState } from 'react'
import type { AppInfo, Application, ConnectionError } from '../../shared/api.ts'
import AgentStatusBar from './AgentStatusBar.tsx'
import AppPicker from './AppPicker.tsx'
import ObjectSpy from './ObjectSpy.tsx'
import ServerSettings from './ServerSettings.tsx'
import { strings } from './strings.ts'

type View =
  | { phase: 'loading'; url?: string }
  | { phase: 'settings'; url: string; failure?: ConnectionError; previous?: View }
  | { phase: 'picker'; url: string; selectedId?: string; missing?: boolean; previous?: View }
  | { phase: 'ready'; url: string; app: Application }

/** After connecting: the saved application if the server still has it, otherwise the picker. */
async function viewForServer(url: string): Promise<View> {
  const { applicationId } = await window.ayna.getSettings()
  if (!applicationId) return { phase: 'picker', url }
  const result = await window.ayna.listApplications()
  // A failed list is shown (with a retry) by the picker itself.
  if (!result.ok) return { phase: 'picker', url, selectedId: applicationId }
  const app = result.apps.find((candidate) => candidate.id === applicationId)
  return app ? { phase: 'ready', url, app } : { phase: 'picker', url, missing: true }
}

export default function App() {
  const [info, setInfo] = useState<AppInfo | null>(null)
  const [error, setError] = useState(false)
  const [view, setView] = useState<View>({ phase: 'loading' })

  useEffect(() => {
    window.ayna.getAppInfo().then(setInfo, () => setError(true))
  }, [])

  // First run shows the settings screen; later runs check the saved server first.
  useEffect(() => {
    let cancelled = false
    async function start() {
      const { serverUrl } = await window.ayna.getSettings()
      if (cancelled) return
      if (!serverUrl) return setView({ phase: 'settings', url: '' })
      setView({ phase: 'loading', url: serverUrl })
      const result = await window.ayna.checkServer(serverUrl)
      if (cancelled) return
      if (!result.ok) return setView({ phase: 'settings', url: serverUrl, failure: result })
      const next = await viewForServer(result.url)
      if (!cancelled) setView(next)
    }
    start().catch(() => !cancelled && setError(true))
    return () => {
      cancelled = true
    }
  }, [])

  function connected(url: string) {
    setView({ phase: 'loading', url })
    viewForServer(url).then(setView, () => setError(true))
  }

  return (
    <main className="app">
      <h1>{strings.appName}</h1>
      <p className="tagline">{strings.tagline}</p>
      <AgentStatusBar />

      {view.phase === 'loading' && !error && (
        <p>{view.url ? strings.checkingSaved(view.url) : strings.loading}</p>
      )}
      {view.phase === 'settings' && (
        <ServerSettings
          initialUrl={view.url}
          initialFailure={view.failure}
          onConnected={connected}
          onCancel={view.previous ? () => setView(view.previous!) : undefined}
        />
      )}
      {(view.phase === 'picker' || view.phase === 'ready') && (
        <section className="card connected">
          <p className="ok">{strings.connectedTo(view.url)}</p>
          <button
            type="button"
            onClick={() => setView({ phase: 'settings', url: view.url, previous: view })}
          >
            {strings.changeServer}
          </button>
        </section>
      )}
      {view.phase === 'picker' && (
        <AppPicker
          selectedId={view.selectedId}
          missing={view.missing}
          onChosen={(app) => setView({ phase: 'ready', url: view.url, app })}
          onCancel={view.previous ? () => setView(view.previous!) : undefined}
        />
      )}
      {view.phase === 'ready' && (
        <section className="card connected">
          <p>{strings.testingApp(view.app.name, view.app.technology)}</p>
          <button
            type="button"
            onClick={() =>
              setView({ phase: 'picker', url: view.url, selectedId: view.app.id, previous: view })
            }
          >
            {strings.changeApplication}
          </button>
        </section>
      )}
      {view.phase === 'ready' && <ObjectSpy />}

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
