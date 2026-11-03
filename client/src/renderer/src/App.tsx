import { useCallback, useEffect, useState, type ReactNode } from 'react'
import type { Application, ConnectionError, CurrentUser } from '../../shared/api.ts'
import type { Language } from '../../shared/language.ts'
import AppPicker from './AppPicker.tsx'
import LanguageMenu, { LanguageContext } from './Language.tsx'
import Login from './Login.tsx'
import ServerSettings from './ServerSettings.tsx'
import Shell from './Shell.tsx'
import { setStringsLanguage, strings } from './strings.ts'

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

export default function App({ initialLanguage }: { initialLanguage: Language }) {
  const [language, setLanguage] = useState(initialLanguage)
  const [languageSaveFailed, setLanguageSaveFailed] = useState(false)
  const [error, setError] = useState(false)
  const [view, setView] = useState<View>({ phase: 'loading' })

  // Switching the texts before the state change makes the re-render below show the new ones.
  const chooseLanguage = useCallback((next: Language) => {
    setStringsLanguage(next)
    document.documentElement.lang = next
    setLanguage(next)
    setLanguageSaveFailed(false)
    window.ayna.setLanguage(next).catch(() => setLanguageSaveFailed(true))
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

  // Stable, because the top bar's menus re-fetch when their callbacks change.
  const sessionEnded = useCallback(
    () =>
      setView((current) =>
        'url' in current && current.url !== undefined
          ? { phase: 'login', url: current.url, ended: true }
          : current,
      ),
    [],
  )

  const languageState = { language, choose: chooseLanguage, saveFailed: languageSaveFailed }
  const content =
    view.phase === 'ready' ? (
      <Shell
        url={view.url}
        user={view.user}
        app={view.app}
        onAppChosen={(app) => setView({ ...view, app })}
        onManageApps={() =>
          setView({
            phase: 'picker',
            url: view.url,
            user: view.user,
            selectedId: view.app.id,
            previous: view,
          })
        }
        onChangeServer={() => setView({ phase: 'settings', url: view.url, previous: view })}
        onUserChanged={(user) => setView({ ...view, user })}
        onSessionEnded={sessionEnded}
        onLogOut={() => logOut(view.url)}
      />
    ) : (
      <Gate>
        {error && (
          <p className="message message-danger" role="alert">
            {strings.bridgeError}
          </p>
        )}
        {view.phase === 'loading' && !error && (
          <p className="hint gate-loading">
            {view.url ? strings.checkingSaved(view.url) : strings.loading}
          </p>
        )}
        {view.phase === 'settings' && (
          <ServerSettings
            initialUrl={view.url}
            initialFailure={view.failure}
            onConnected={connected}
            onCancel={view.previous ? () => setView(view.previous!) : undefined}
          />
        )}
        {view.phase === 'login' && (
          <Login
            url={view.url}
            ended={view.ended}
            onLoggedIn={() => connected(view.url)}
            onChangeServer={() => setView({ phase: 'settings', url: view.url, previous: view })}
          />
        )}
        {view.phase === 'picker' && (
          <AppPicker
            selectedId={view.selectedId}
            missing={view.missing}
            onChosen={(app) => setView({ phase: 'ready', url: view.url, user: view.user, app })}
            onSessionEnded={sessionEnded}
            onCancel={view.previous ? () => setView(view.previous!) : undefined}
          />
        )}
      </Gate>
    )
  return <LanguageContext value={languageState}>{content}</LanguageContext>
}

/** Before the shell (server, login, first application): one centred card under the name. */
function Gate({ children }: { children: ReactNode }) {
  return (
    <main className="gate">
      {/* The language can be chosen before connecting, on the very first screen. */}
      <div className="gate-language">
        <LanguageMenu />
      </div>
      <div className="gate-brand">
        <span className="brand">AYNA</span>
        <p className="hint">{strings.tagline}</p>
      </div>
      {children}
    </main>
  )
}
