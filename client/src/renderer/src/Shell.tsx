import { useEffect, useState } from 'react'
import type { AppVersion, Application, CurrentUser } from '../../shared/api.ts'
import AgentStatusBar from './AgentStatusBar.tsx'
import AppMenu from './AppMenu.tsx'
import Icon, { type IconName } from './Icons.tsx'
import Menu from './Menu.tsx'
import ObjectSpy from './ObjectSpy.tsx'
import Page from './Page.tsx'
import SettingsPage from './SettingsPage.tsx'
import { strings } from './strings.ts'
import Users from './Users.tsx'
import VersionMenu from './VersionMenu.tsx'

type Place = keyof typeof strings.nav
type LaterPlace = keyof typeof strings.laterPlaces

/** Navigation in task order (docs/ui/wireframes.md §0); `issue` = built later by that issue. */
const PLACES: { place: Place; icon: IconName; issue?: number }[] = [
  { place: 'spy', icon: 'spy' },
  { place: 'repository', icon: 'repository', issue: 30 },
  { place: 'tests', icon: 'tests', issue: 38 },
  { place: 'runs', icon: 'runs', issue: 68 },
  { place: 'repairs', icon: 'repairs', issue: 75 },
  { place: 'changes', icon: 'changes', issue: 81 },
]

interface Props {
  url: string
  user: CurrentUser
  app: Application
  onAppChosen(app: Application): void
  onManageApps(): void
  onChangeServer(): void
  onUserChanged(user: CurrentUser): void
  onSessionEnded(): void
  onLogOut(): void
}

/**
 * The client's frame after login (#183): a top bar for the context every screen shares
 * (application, version, agent, language, user) and a navigation of places.
 */
export default function Shell(props: Props) {
  const { url, user, app, onSessionEnded } = props
  const [place, setPlace] = useState<Place>('spy')
  const [version, setVersion] = useState<AppVersion>()
  const admin = user.role === 'admin'

  // Ctrl+1…Ctrl+6 go to the places in order.
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if (!event.ctrlKey || event.altKey || event.shiftKey) return
      const target = PLACES[Number(event.key) - 1]
      if (!target) return
      event.preventDefault()
      setPlace(target.place)
    }
    document.addEventListener('keydown', key)
    return () => document.removeEventListener('keydown', key)
  }, [])

  function navItem(target: Place, icon: IconName, issue?: number) {
    return (
      <li key={target}>
        <button
          type="button"
          className={['nav-item', target === place && 'current', issue && 'later']
            .filter(Boolean)
            .join(' ')}
          aria-current={target === place ? 'page' : undefined}
          title={strings.nav[target]}
          onClick={() => setPlace(target)}
        >
          <Icon name={icon} />
          <span className="nav-label">{strings.nav[target]}</span>
          {issue && <span className="pill pill-muted nav-later">{strings.later}</span>}
        </button>
      </li>
    )
  }

  const later = PLACES.find((candidate) => candidate.place === place)?.issue
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">AYNA</span>
        <AppMenu
          app={app}
          onChosen={(next) => {
            setVersion(undefined)
            props.onAppChosen(next)
          }}
          onManage={props.onManageApps}
          onSessionEnded={onSessionEnded}
        />
        <VersionMenu
          key={app.id}
          appId={app.id}
          version={version}
          onChange={setVersion}
          onSessionEnded={onSessionEnded}
        />
        <span className="topbar-gap" />
        <AgentStatusBar />
        <button type="button" className="menu-button" disabled title={strings.topLanguageHint}>
          {strings.topLanguage}
        </button>
        <Menu
          title={user.username}
          align="end"
          label={
            <>
              {user.username}
              <Icon name="chevron" />
            </>
          }
        >
          {() => (
            <div className="menu-body">
              <p className="hint">
                {strings.topLoggedIn(user.username, strings.roles[user.role], url)}
              </p>
              <button type="button" onClick={props.onLogOut}>
                {strings.logOut}
              </button>
            </div>
          )}
        </Menu>
      </header>

      <nav className="nav" aria-label={strings.navLabel}>
        <ul>{PLACES.map(({ place: target, icon, issue }) => navItem(target, icon, issue))}</ul>
        <ul className="nav-bottom">
          {admin && navItem('users', 'users')}
          {navItem('settings', 'settings')}
        </ul>
      </nav>

      <main className="work">
        {place === 'spy' && <ObjectSpy app={app} version={version} />}
        {later && <Later place={place as LaterPlace} issue={later} />}
        {place === 'users' && (
          <Users user={user} onSessionEnded={onSessionEnded} onUserChanged={props.onUserChanged} />
        )}
        {place === 'settings' && <SettingsPage url={url} onChangeServer={props.onChangeServer} />}
      </main>
    </div>
  )
}

/** A place whose screen is not built yet: what it will do and which issue builds it. */
function Later({ place, issue }: { place: LaterPlace; issue: number }) {
  return (
    <Page
      title={strings.nav[place]}
      actions={<span className="pill pill-muted">{strings.later}</span>}
    >
      <div className="empty">
        <p className="empty-title">{strings.laterPlaces[place]}</p>
        <p className="hint">{strings.laterIssue(issue)}</p>
      </div>
    </Page>
  )
}
