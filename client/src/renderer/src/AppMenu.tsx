import { useEffect, useState } from 'react'
import type { Application, RequestFailure } from '../../shared/api.ts'
import Icon from './Icons.tsx'
import Menu from './Menu.tsx'
import { strings } from './strings.ts'

type List =
  | { state: 'loading' }
  | { state: 'loaded'; apps: Application[] }
  | { state: 'failed'; reason: RequestFailure }

/** The top bar's application switch: the server's applications, fetched each time it opens. */
export default function AppMenu({
  app,
  onChosen,
  onManage,
  onSessionEnded,
}: {
  app: Application
  onChosen: (app: Application) => void
  /** Opens the full picker, where an application can also be added. */
  onManage: () => void
  onSessionEnded: () => void
}) {
  return (
    <Menu
      title={strings.topApplication}
      className="app-switch"
      label={
        <>
          <strong>{app.name}</strong>
          <Icon name="chevron" />
        </>
      }
    >
      {(close) => (
        <Choices
          current={app}
          onChosen={(next) => {
            close()
            if (next.id !== app.id) onChosen(next)
          }}
          onManage={() => {
            close()
            onManage()
          }}
          onSessionEnded={onSessionEnded}
        />
      )}
    </Menu>
  )
}

function Choices({
  current,
  onChosen,
  onManage,
  onSessionEnded,
}: {
  current: Application
  onChosen: (app: Application) => void
  onManage: () => void
  onSessionEnded: () => void
}) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [chooseFailed, setChooseFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    window.ayna.listApplications().then(
      (result) => {
        if (cancelled) return
        if (result.ok) setList({ state: 'loaded', apps: result.apps })
        else if (result.reason === 'unauthorized') onSessionEnded()
        else setList({ state: 'failed', reason: result.reason })
      },
      () => !cancelled && setList({ state: 'failed', reason: 'unreachable' }),
    )
    return () => {
      cancelled = true
    }
  }, [onSessionEnded])

  async function choose(app: Application) {
    setChooseFailed(false)
    try {
      await window.ayna.chooseApplication(app.id)
      onChosen(app)
    } catch {
      setChooseFailed(true)
    }
  }

  return (
    <div className="menu-body">
      <p className="menu-title">{strings.topApplications}</p>
      {list.state === 'loading' && <p className="hint">{strings.loading}</p>}
      {list.state === 'failed' && (
        <p className="field-error" role="alert">
          {strings.requestErrors[list.reason]}
        </p>
      )}
      {list.state === 'loaded' && (
        <ul className="choice-list">
          {list.apps.map((app) => (
            <li key={app.id}>
              <button
                type="button"
                className={app.id === current.id ? 'selected' : undefined}
                aria-pressed={app.id === current.id}
                onClick={() => choose(app)}
              >
                <span>{app.name}</span>
                <span className="hint">{app.technology}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {chooseFailed && (
        <p className="field-error" role="alert">
          {strings.chooseFailed}
        </p>
      )}
      <button type="button" className="btn-quiet" onClick={onManage}>
        {strings.topManageApps}
      </button>
    </div>
  )
}
