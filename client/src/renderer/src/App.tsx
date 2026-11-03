import { useEffect, useState } from 'react'
import type { AppInfo, Application, ConnectionError, CurrentUser } from '../../shared/api.ts'
import AgentStatusBar from './AgentStatusBar.tsx'
import AppPicker from './AppPicker.tsx'
import ObjectSpy from './ObjectSpy.tsx'
import Login from './Login.tsx'
import ServerSettings from './ServerSettings.tsx'
import Users from './Users.tsx'
import { strings } from './strings.ts'

type View =
  | { phase: 'loading'; url?: string }
  | { phase: 'settings'; url: string; failure?: ConnectionError; previous?: View }
  | { phase: 'login'; url: string; ended?: boolean }
  | {
      phase: 'picker'
      url: string
      user: CurrentUser
      selectedId?: string
      missing?: boolean
      previous?: View
    }
  | { phase: 'ready'; url: string; user: CurrentUser; app: Application }
  | { phase: 'users'; url: string; user: CurrentUser; previous: SignedIn }

type SignedIn = Extract<View, { phase: 'picker' | 'ready' }>

/**
 * After connecting: the login screen without a session (#60), then the saved application
 * if the server still has it, otherwise the picker.
 */
async function viewForServer(url: string): Promise<View> {
  const user = await window.ayna.currentUser()
  if (!user) return { phase: 'login', url }
  const { applicationId } = await window.ayna.getSettings()
  if (!applicationId) return { phase: 'picker', url, user }
  const result = await window.ayna.listApplications()
  if (!result.ok && result.reason === 'unauthorized') return { phase: 'login', url, ended: true }
  // Other failures are shown (with a retry) by the picker itself.
  if (!result.ok) return { phase: 'picker', url, user, selectedId: applicationId }
  const app = result.apps.find((candidate) => candidate.id === applicationId)
  return app ? { phase: 'ready', url, user, app } : { phase: 'picker', url, user, missing: true }
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

  async function logOut(url: string) {
    await window.ayna.logout().catch(() => undefined)
    setView({ phase: 'login', url })
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
      {(view.phase === 'login' ||
        view.phase === 'picker' ||
        view.phase === 'ready' ||
        view.phase === 'users') && (
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
      {view.phase === 'login' && (
        <Login url={view.url} ended={view.ended} onLoggedIn={() => connected(view.url)} />
      )}
      {(view.phase === 'picker' || view.phase === 'ready' || view.phase === 'users') && (
        <section className="card connected">
          <p>{strings.signedInAs(view.user.username, view.user.role)}</p>
          <span className="actions">
            {view.phase !== 'users' && (
              <button
                type="button"
                onClick={() =>
                  setView({ phase: 'users', url: view.url, user: view.user, previous: view })
                }
              >
                {strings.manageUsers}
              </button>
            )}
            <button type="button" onClick={() => logOut(view.url)}>
              {strings.logOut}
            </button>
          </span>
        </section>
      )}
      {view.phase === 'users' && (
        <Users
          user={view.user}
          onSessionEnded={() => setView({ phase: 'login', url: view.url, ended: true })}
          onUserChanged={(user) => setView({ ...view, user, previous: { ...view.previous, user } })}
          onClose={() => setView(view.previous)}
        />
      )}
      {view.phase === 'picker' && (
        <AppPicker
          selectedId={view.selectedId}
          missing={view.missing}
          onChosen={(app) => setView({ phase: 'ready', url: view.url, user: view.user, app })}
          onSessionEnded={() => setView({ phase: 'login', url: view.url, ended: true })}
          onCancel={view.previous ? () => setView(view.previous!) : undefined}
        />
      )}
      {view.phase === 'ready' && (
        <section className="card connected">
          <p>{strings.testingApp(view.app.name, view.app.technology)}</p>
          <button
            type="button"
            onClick={() =>
              setView({
                phase: 'picker',
                url: view.url,
                user: view.user,
                selectedId: view.app.id,
                previous: view,
              })
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
