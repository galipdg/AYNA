import { useEffect, useState, type FormEvent } from 'react'
import type {
  AppVersion,
  Application,
  RepoObjectDetails,
  RepoObjectError,
  RepoObjectSummary,
} from '../../shared/api.ts'
import { logicalNameProblem, type IdentifyingField } from '../../shared/repository.ts'
import { foldText } from '../../shared/tree.ts'
import Page from './Page.tsx'
import { ElementFacts } from './PropertyPanel.tsx'
import {
  FoundBy,
  PropertyTable,
  objectRows,
  propertySet,
  rowProblems,
  type Row,
} from './PropertySetEditor.tsx'
import { controlTypeLabel, repoObjectErrorText, strings } from './strings.ts'

type List =
  | { state: 'loading' }
  | { state: 'loaded'; objects: RepoObjectSummary[] }
  | { state: 'failed'; problems: string[] }

/** The part of a logical name before the dot: the screen the element is on. */
function screenOf(name: string): string {
  const dot = name.indexOf('.')
  return dot < 0 ? name : name.slice(0, dot)
}

function leafOf(name: string): string {
  return name.slice(name.indexOf('.') + 1)
}

/** Search by name, label or type, the type also in plain words ("text box" finds Edit). */
function matchesQuery(object: RepoObjectSummary, query: string): boolean {
  const { name, nearestLabel, controlType } = object
  const text = [name, nearestLabel, controlType, controlType && controlTypeLabel(controlType)]
  return foldText(text.filter(Boolean).join(' ')).includes(foldText(query))
}

/** The objects by screen, in name order (the server sorts by name). */
function byScreen(objects: RepoObjectSummary[]): [string, RepoObjectSummary[]][] {
  const groups = new Map<string, RepoObjectSummary[]>()
  for (const object of objects) {
    const screen = screenOf(object.name)
    groups.set(screen, [...(groups.get(screen) ?? []), object])
  }
  return [...groups]
}

/**
 * The application's object repository (#30, wireframe §5): saved elements grouped by screen
 * with how many tests use each (FR-08); the chosen one's details, where it can be renamed,
 * edited or removed (FR-09). New elements are added from the Object Spy.
 */
export default function Repository({
  app,
  onOpenSpy,
  onSessionEnded,
}: {
  app: Application
  onOpenSpy: () => void
  onSessionEnded: () => void
}) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [versions, setVersions] = useState<AppVersion[]>([])
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string>()
  const [notice, setNotice] = useState<string>()

  // Entering `loading` (first render, Reload, after a change) fetches the list.
  const loading = list.state === 'loading'
  useEffect(() => {
    if (!loading) return
    let cancelled = false
    window.ayna
      .listRepoObjects(app.id)
      .then((result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        setList(
          result.ok
            ? { state: 'loaded', objects: result.objects }
            : { state: 'failed', problems: repoObjectErrorText(result) },
        )
        // Someone else may have removed the chosen object.
        if (result.ok) {
          setSelectedId((id) => result.objects.find((object) => object.id === id)?.id)
        }
      })
      .catch(() => {
        if (!cancelled) setList({ state: 'failed', problems: [strings.bridgeError] })
      })
    return () => {
      cancelled = true
    }
  }, [loading, app.id, onSessionEnded])

  // "Captured in versions" lists every version; a failure only leaves that row empty.
  useEffect(() => {
    let cancelled = false
    window.ayna
      .listVersions(app.id)
      .then((result) => {
        if (!cancelled && result.ok) setVersions(result.versions)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [app.id])

  function choose(id: string) {
    setSelectedId(id)
    setNotice(undefined)
  }

  function changed(text: string) {
    setNotice(text)
    setList({ state: 'loading' })
  }

  function removed(text: string) {
    setSelectedId(undefined)
    changed(text)
  }

  const objects = list.state === 'loaded' ? list.objects : []
  const search = query.trim()
  const shown = objects.filter((object) => matchesQuery(object, search))
  const openSpy = (
    <button type="button" onClick={onOpenSpy}>
      {strings.repoViewOpenSpy}
    </button>
  )
  return (
    <Page title={strings.nav.repository} help={strings.repoViewHelp(app.name)} actions={openSpy}>
      <div className="repository">
        <section className="panel spy-panel" aria-label={strings.nav.repository}>
          <input
            type="search"
            aria-label={strings.repoViewSearch}
            placeholder={strings.repoViewSearch}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={objects.length === 0}
          />
          <div className="panel-scroll">
            {loading && <p className="hint">{strings.loading}</p>}
            {list.state === 'failed' && (
              <div className="message message-danger" role="alert">
                {list.problems.map((problem) => (
                  <p key={problem}>{problem}</p>
                ))}
                <button type="button" onClick={() => setList({ state: 'loading' })}>
                  {strings.repoViewReload}
                </button>
              </div>
            )}
            {list.state === 'loaded' && objects.length === 0 && (
              <div className="empty">
                <p className="empty-title">{strings.repoViewEmpty}</p>
                {openSpy}
              </div>
            )}
            {objects.length > 0 && shown.length === 0 && (
              <p className="hint">{strings.repoViewNoMatch(search)}</p>
            )}
            {byScreen(shown).map(([screen, items]) => (
              <details key={screen} className="repo-group" open>
                <summary>
                  {screen} <span className="hint">({items.length})</span>
                </summary>
                <ul className="choice-list">
                  {items.map((object) => (
                    <li key={object.id}>
                      <button
                        type="button"
                        className={object.id === selectedId ? 'selected' : undefined}
                        aria-pressed={object.id === selectedId}
                        title={object.name}
                        onClick={() => choose(object.id)}
                      >
                        <span>{leafOf(object.name)}</span>
                        <span className="hint">{strings.repoViewTests(object.testCount)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
          {objects.length > 0 && (
            <footer className="panel-footer">
              <p className="hint">{strings.repoViewCount(objects.length)}</p>
            </footer>
          )}
        </section>

        <section className="panel spy-panel" aria-label={strings.spyPropertiesTitle}>
          {selectedId ? (
            <ObjectDetails
              key={selectedId}
              id={selectedId}
              versions={versions}
              notice={notice}
              onChanged={changed}
              onRemoved={removed}
              onSessionEnded={onSessionEnded}
            />
          ) : (
            <div className="empty">
              {notice && (
                <p className="message message-success" role="status">
                  {notice}
                </p>
              )}
              {objects.length > 0 && <p className="empty-title">{strings.repoViewChoose}</p>}
            </div>
          )}
        </section>
      </div>
    </Page>
  )
}

type Detail =
  | { state: 'loading' }
  | { state: 'loaded'; object: RepoObjectDetails }
  | { state: 'failed'; problems: string[] }

type Mode = 'view' | 'rename' | 'edit' | 'remove'

/** One saved element: what it is, which tests use it, how AYNA finds it. */
function ObjectDetails({
  id,
  versions,
  notice,
  onChanged,
  onRemoved,
  onSessionEnded,
}: {
  id: string
  versions: AppVersion[]
  notice?: string
  onChanged: (notice: string) => void
  onRemoved: (notice: string) => void
  onSessionEnded: () => void
}) {
  const [detail, setDetail] = useState<Detail>({ state: 'loading' })
  const [mode, setMode] = useState<Mode>('view')
  const [name, setName] = useState('')
  const [rows, setRows] = useState<Row[]>([])
  const [busy, setBusy] = useState(false)
  const [problems, setProblems] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    window.ayna
      .getRepoObject(id)
      .then((result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        setDetail(
          result.ok
            ? { state: 'loaded', object: result.object }
            : { state: 'failed', problems: repoObjectErrorText(result) },
        )
      })
      .catch(() => {
        if (!cancelled) setDetail({ state: 'failed', problems: [strings.bridgeError] })
      })
    return () => {
      cancelled = true
    }
  }, [id, onSessionEnded])

  if (detail.state === 'loading') return <p className="hint">{strings.loading}</p>
  if (detail.state === 'failed') {
    return (
      <div className="message message-danger" role="alert">
        {detail.problems.map((problem) => (
          <p key={problem}>{problem}</p>
        ))}
      </div>
    )
  }
  const { object } = detail

  function start(next: Mode) {
    setMode(next)
    setProblems([])
    if (next === 'rename') setName(object.name)
    if (next === 'edit') setRows(objectRows(object))
  }

  /** Runs one change; a failure stays in this mode with the reasons shown. */
  async function run<T extends { ok: true } | RepoObjectError>(
    call: () => Promise<T>,
    done: (result: Extract<T, { ok: true }>) => void,
  ) {
    setBusy(true)
    try {
      const result = await call()
      if (result.ok) return done(result as Extract<T, { ok: true }>)
      const error = result as RepoObjectError
      if (error.reason === 'unauthorized') return onSessionEnded()
      setProblems(repoObjectErrorText(error))
    } catch {
      setProblems([strings.bridgeError])
    } finally {
      setBusy(false)
    }
  }

  function rename(event: FormEvent) {
    event.preventDefault()
    const next = name.trim()
    if (next === object.name) return setMode('view')
    const problem = logicalNameProblem(next)
    if (problem) return setProblems([strings.repoNameProblems[problem]])
    run(
      () => window.ayna.updateRepoObject(id, { name: next }),
      (result) => {
        setDetail({ state: 'loaded', object: result.object })
        setMode('view')
        onChanged(strings.repoViewRenamed(result.object.name))
      },
    )
  }

  function saveEdit(event: FormEvent) {
    event.preventDefault()
    const found = rowProblems(rows)
    const primary = propertySet(rows, 'primary')
    const fallback = propertySet(rows, 'fallback')
    if (found.length || typeof primary === 'string' || typeof fallback === 'string') {
      return setProblems(found)
    }
    run(
      () => window.ayna.updateRepoObject(id, { primary, fallback }),
      (result) => {
        setDetail({ state: 'loaded', object: result.object })
        setMode('view')
        onChanged(strings.repoViewUpdated(result.object.name))
      },
    )
  }

  function remove() {
    run(
      () => window.ayna.deleteRepoObject(id),
      () => onRemoved(strings.repoViewRemoved(object.name)),
    )
  }

  function change(field: IdentifyingField, update: Partial<Row>) {
    setRows((current) => current.map((row) => (row.field === field ? { ...row, ...update } : row)))
  }

  const { element, usedBy } = object
  const what = [element.controlType && controlTypeLabel(element.controlType), element.windowTitle]
  const problemList = problems.length > 0 && (
    <ul className="message message-danger" role="alert">
      {problems.map((problem) => (
        <li key={problem}>{problem}</li>
      ))}
    </ul>
  )

  if (mode === 'edit') {
    return (
      <form className="repo-form" onSubmit={saveEdit}>
        <header className="panel-header">
          <div className="element-title">
            <h2>{object.name}</h2>
            <p className="hint">{strings.repoFoundBy}</p>
          </div>
        </header>
        <div className="panel-scroll form">
          <p className="hint">{strings.repoViewEditHint}</p>
          <FoundBy rows={rows} />
          <PropertyTable rows={rows} onChange={change} />
          {problemList}
        </div>
        <footer className="panel-footer form-actions">
          <button type="button" onClick={() => setMode('view')} disabled={busy}>
            {strings.repoCancel}
          </button>
          <button type="submit" className="btn-main" disabled={busy}>
            {busy ? strings.repoSaving : strings.repoSave}
          </button>
        </footer>
      </form>
    )
  }

  return (
    <>
      <header className="panel-header">
        {mode === 'rename' ? (
          <form className="inline-form" onSubmit={rename}>
            <label htmlFor="repo-rename" className="visually-hidden">
              {strings.repoViewRenameLabel}
            </label>
            <input
              id="repo-rename"
              value={name}
              onChange={(event) => setName(event.target.value)}
              aria-describedby="repo-rename-hint"
              autoFocus
            />
            <button type="submit" className="btn-main" disabled={busy}>
              {busy ? strings.repoSaving : strings.repoSave}
            </button>
            <button type="button" onClick={() => setMode('view')} disabled={busy}>
              {strings.repoCancel}
            </button>
          </form>
        ) : (
          <>
            <div className="element-title">
              <h2>{object.name}</h2>
              <p className="hint">{what.filter(Boolean).join(' · ')}</p>
            </div>
            <button type="button" onClick={() => start('rename')}>
              {strings.repoViewRename}
            </button>
          </>
        )}
      </header>
      <div className="panel-scroll">
        {mode === 'rename' && (
          <p id="repo-rename-hint" className="hint">
            {strings.repoViewRenameHint}
          </p>
        )}
        {mode === 'view' && notice && (
          <p className="message message-success" role="status">
            {notice}
          </p>
        )}
        {mode !== 'remove' && problemList}

        <h4>{strings.repoViewUsedBy(usedBy.length)}</h4>
        {usedBy.length > 0 && (
          <ul className="repo-used-by">
            {usedBy.map((test) => (
              <li key={test.id}>{test.name}</li>
            ))}
          </ul>
        )}

        <h4>{strings.repoFoundBy}</h4>
        <FoundBy rows={objectRows(object)} />

        {versions.length > 0 && (
          <>
            <h4>{strings.repoViewCapturedIn}</h4>
            <ul className="repo-versions">
              {versions.map((version) => {
                const captured = object.versionIds.includes(version.id)
                const label = captured
                  ? strings.repoViewCapturedHere
                  : strings.repoViewNotCapturedHere
                return (
                  <li key={version.id} className={captured ? 'tone-success' : 'hint'} title={label}>
                    {version.version} <span aria-hidden="true">{captured ? '✓' : '–'}</span>
                    <span className="visually-hidden">{label}</span>
                  </li>
                )
              })}
            </ul>
          </>
        )}

        <details className="advanced">
          <summary>{strings.repoViewCaptured}</summary>
          <ElementFacts element={element} />
        </details>
      </div>
      <footer className="panel-footer">
        {mode === 'remove' ? (
          <div className="message message-danger">
            <p>{strings.repoViewRemoveConfirm(object.name)}</p>
            {problemList}
            <div className="form-actions">
              <button type="button" onClick={() => setMode('view')} disabled={busy}>
                {strings.repoCancel}
              </button>
              <button type="button" className="btn-danger" onClick={remove} disabled={busy}>
                {strings.repoViewRemove}
              </button>
            </div>
          </div>
        ) : (
          <div className="form-actions">
            <button type="button" className="btn-danger" onClick={() => start('remove')}>
              {strings.repoViewRemove}
            </button>
            <button type="button" className="btn-main" onClick={() => start('edit')}>
              {strings.repoViewEdit}
            </button>
          </div>
        )}
      </footer>
    </>
  )
}
