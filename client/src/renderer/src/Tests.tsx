import {
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import type {
  Application,
  AppVersion,
  RepoObjectSummary,
  TestCase,
  TestError,
  TestSummary,
} from '../../shared/api.ts'
import {
  documentFrom,
  draftsFrom,
  localProblems,
  renamedTargets,
  serverProblems,
  unique,
  withRenamedTargets,
  withStoredIds,
  withTimeoutsIn,
  type DraftStep,
  type StepDocument,
  type StepProblem,
} from '../../shared/steps.ts'
import {
  historyCommand,
  mapHistory,
  record,
  redo,
  startHistory,
  undo,
} from '../../shared/history.ts'
import { foldText } from '../../shared/tree.ts'
import { LanguageContext } from './Language.tsx'
import Page from './Page.tsx'
import Resizer from './Resizer.tsx'
import RunBar, { useLiveRun } from './RunBar.tsx'
import StepTable, { problemText } from './StepTable.tsx'
import { formatDate, formatTime, runsErrorText, strings, testErrorText } from './strings.ts'
import { rowState } from '../../shared/liveRun.ts'

type List =
  | { state: 'loading' }
  | { state: 'loaded'; tests: TestSummary[] }
  | { state: 'failed'; problem: string }

type Objects =
  { state: 'loading' } | { state: 'loaded'; objects: RepoObjectSummary[] } | { state: 'failed' }

/**
 * The application's tests (#38, wireframe §6): the list on the left, the chosen test's steps
 * in a codeless table on the right. Steps are checked against the step schema while they are
 * edited and saved as a whole.
 */
/** The test list can be narrowed to give the steps more room. */
const LIST_WIDTH = { initial: 220, min: 150, max: 420 }

/** The last width chosen, kept while the app runs, as for the step table's columns. */
let chosenListWidth: number = LIST_WIDTH.initial

export default function Tests({
  app,
  active,
  version,
  onSessionEnded,
}: {
  app: Application
  /** The version chosen in the top bar; a run plays against it (#44). */
  version?: AppVersion
  /** Whether the place is shown; it stays mounted so unsaved steps survive a visit elsewhere. */
  active: boolean
  onSessionEnded: () => void
}) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [listWidth, setListWidth] = useState(chosenListWidth)
  const [objects, setObjects] = useState<Objects>({ state: 'loading' })
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string>()
  const [dirty, setDirty] = useState(false)
  /** The test to open once the user agrees to leave unsaved changes. */
  const [leaveTo, setLeaveTo] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [createProblem, setCreateProblem] = useState<string>()
  const [busy, setBusy] = useState(false)

  const loading = list.state === 'loading'
  useEffect(() => {
    if (!loading) return
    let cancelled = false
    window.ayna
      .listTests(app.id)
      .then((result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        setList(
          result.ok
            ? { state: 'loaded', tests: result.tests }
            : { state: 'failed', problem: testErrorText(result) },
        )
      })
      .catch(() => {
        if (!cancelled) setList({ state: 'failed', problem: strings.bridgeError })
      })
    return () => {
      cancelled = true
    }
  }, [loading, app.id, onSessionEnded])

  // The element menu: loaded again each time the place is shown, since elements are added in
  // the Object Spy and renamed in the Repository.
  useEffect(() => {
    if (!active) return
    let cancelled = false
    window.ayna
      .listRepoObjects(app.id)
      .then((result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        setObjects(result.ok ? { state: 'loaded', objects: result.objects } : { state: 'failed' })
      })
      .catch(() => {
        if (!cancelled) setObjects({ state: 'failed' })
      })
    return () => {
      cancelled = true
    }
  }, [active, app.id, onSessionEnded])

  function open(id: string | undefined) {
    setSelectedId(id)
    setLeaveTo(undefined)
    setDirty(false)
    setNotice(undefined)
  }

  function choose(id: string) {
    if (id === selectedId) return
    if (dirty) return setLeaveTo(id)
    open(id)
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    const name = newName.trim()
    if (!name) return setCreateProblem(strings.testsNameBlank)
    setBusy(true)
    try {
      const result = await window.ayna.createTest(app.id, name)
      if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
      if (!result.ok) return setCreateProblem(testErrorText(result))
      setCreating(false)
      setNewName('')
      setCreateProblem(undefined)
      setList({ state: 'loading' })
      if (dirty) setLeaveTo(result.test.id)
      else open(result.test.id)
    } catch {
      setCreateProblem(strings.bridgeError)
    } finally {
      setBusy(false)
    }
  }

  const tests = list.state === 'loaded' ? list.tests : []
  const search = query.trim()
  const shown = tests.filter((test) => foldText(test.name).includes(foldText(search)))
  const leaving = tests.find((test) => test.id === selectedId)
  const newTest = (
    <button
      type="button"
      className="btn-main"
      onClick={() => {
        setCreating(true)
        setCreateProblem(undefined)
      }}
    >
      + {strings.testsNew}
    </button>
  )

  function resizeList(width: number) {
    chosenListWidth = Math.round(Math.min(LIST_WIDTH.max, Math.max(LIST_WIDTH.min, width)))
    setListWidth(chosenListWidth)
  }

  return (
    <Page title={strings.nav.tests} help={strings.testsHelp(app.name)} actions={newTest}>
      <div className="tests" style={{ '--test-list-width': `${listWidth}px` } as CSSProperties}>
        <section className="panel spy-panel" aria-label={strings.nav.tests}>
          {creating && (
            <form className="form" onSubmit={create}>
              <label htmlFor="test-new">{strings.testsNewLabel}</label>
              <input
                id="test-new"
                value={newName}
                placeholder={strings.testsNewPlaceholder}
                aria-invalid={createProblem ? true : undefined}
                onChange={(event) => setNewName(event.target.value)}
                onKeyDown={(event) => event.key === 'Escape' && setCreating(false)}
                autoFocus
              />
              {createProblem && (
                <p className="field-error" role="alert">
                  {createProblem}
                </p>
              )}
              <div className="form-actions">
                <button type="button" onClick={() => setCreating(false)} disabled={busy}>
                  {strings.testsCancel}
                </button>
                <button type="submit" className="btn-main" disabled={busy}>
                  {strings.testsCreate}
                </button>
              </div>
            </form>
          )}
          <input
            type="search"
            aria-label={strings.testsSearch}
            placeholder={strings.testsSearch}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={tests.length === 0}
          />
          <div className="panel-scroll">
            {loading && <p className="hint">{strings.loading}</p>}
            {list.state === 'failed' && (
              <div className="message message-danger" role="alert">
                <p>{list.problem}</p>
                <button type="button" onClick={() => setList({ state: 'loading' })}>
                  {strings.testsReload}
                </button>
              </div>
            )}
            {list.state === 'loaded' && tests.length === 0 && !creating && (
              <div className="empty">
                <p className="empty-title">{strings.testsEmpty}</p>
              </div>
            )}
            {tests.length > 0 && shown.length === 0 && (
              <p className="hint">{strings.testsNoMatch(search)}</p>
            )}
            <ul className="choice-list">
              {shown.map((test) => (
                <li key={test.id}>
                  <button
                    type="button"
                    className={['two-line', test.id === selectedId && 'selected']
                      .filter(Boolean)
                      .join(' ')}
                    aria-pressed={test.id === selectedId}
                    onClick={() => choose(test.id)}
                  >
                    <span>
                      {test.name}
                      {test.id === selectedId && dirty && (
                        <span className="unsaved-dot" title={strings.testsUnsaved}>
                          {' '}
                          ●
                        </span>
                      )}
                    </span>
                    <span className="hint">{strings.testsSteps(test.stepCount)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          {tests.length > 0 && (
            <footer className="panel-footer">
              <p className="hint">{strings.testsCount(tests.length)}</p>
            </footer>
          )}
        </section>

        <Resizer
          className="pane-resizer"
          label={strings.testsListResize}
          width={listWidth}
          initial={LIST_WIDTH.initial}
          min={LIST_WIDTH.min}
          max={LIST_WIDTH.max}
          onResize={resizeList}
        />

        <section className="panel spy-panel" aria-label={strings.stepsLabel}>
          {leaveTo && (
            <div className="message message-warning" role="alertdialog">
              <p>{strings.testsLeaveConfirm(leaving?.name ?? '')}</p>
              <div className="form-actions">
                <button type="button" onClick={() => setLeaveTo(undefined)}>
                  {strings.testsStay}
                </button>
                <button type="button" className="btn-danger" onClick={() => open(leaveTo)}>
                  {strings.testsLeave}
                </button>
              </div>
            </div>
          )}
          {selectedId ? (
            <TestEditor
              key={selectedId}
              id={selectedId}
              version={version}
              objects={objects}
              onDirty={setDirty}
              onChanged={() => setList({ state: 'loading' })}
              onDeleted={(name) => {
                open(undefined)
                setNotice(strings.testsDeleted(name))
                setList({ state: 'loading' })
              }}
              onSessionEnded={onSessionEnded}
            />
          ) : (
            <div className="empty">
              {notice && (
                <p className="message message-success" role="status">
                  {notice}
                </p>
              )}
              {tests.length > 0 && <p className="empty-title">{strings.testsChoose}</p>}
            </div>
          )}
        </section>
      </div>
    </Page>
  )
}

type Detail =
  { state: 'loading' } | { state: 'loaded'; test: TestCase } | { state: 'failed'; problem: string }

type Mode = 'view' | 'rename' | 'delete'

/** The document as the editor would save it, as text, to see whether anything changed. */
function fingerprint(document: StepDocument): string {
  return JSON.stringify(documentFrom(draftsFrom(document, strings.locale)))
}

/** A fingerprint with its steps' elements renamed, as the server renamed the stored steps. */
function renamedFingerprint(text: string, renames: Map<string, string>): string {
  if (!text) return text
  const document = JSON.parse(text) as StepDocument
  const steps = document.steps.map((step) => {
    const target = renames.get(step.target)
    return target === undefined ? step : { ...step, target }
  })
  return JSON.stringify({ ...document, steps })
}

/** One test: its name and its steps, edited in place and saved together. */
function TestEditor({
  id,
  version,
  objects,
  onDirty,
  onChanged,
  onDeleted,
  onSessionEnded,
}: {
  id: string
  version?: AppVersion
  objects: Objects
  onDirty: (dirty: boolean) => void
  onChanged: () => void
  onDeleted: (name: string) => void
  onSessionEnded: () => void
}) {
  const [detail, setDetail] = useState<Detail>({ state: 'loading' })
  const [history, setHistory] = useState(() => startHistory<DraftStep[]>([]))
  const drafts = history.present
  const editor = useRef<HTMLDivElement>(null)
  const [saved, setSaved] = useState('')
  const [schemaIssues, setSchemaIssues] = useState<StepProblem[]>([])
  /** What the server refused at the last save; cleared by the next edit. */
  const [serverIssues, setServerIssues] = useState<StepProblem[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [notice, setNotice] = useState<string>()
  const [mode, setMode] = useState<Mode>('view')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const live = useLiveRun(id)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    let cancelled = false
    window.ayna
      .getTest(id)
      .then((result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        if (!result.ok) return setDetail({ state: 'failed', problem: testErrorText(result) })
        setDetail({ state: 'loaded', test: result.test })
        setHistory(startHistory(draftsFrom(result.test.document, strings.locale)))
        setSaved(fingerprint(result.test.document))
      })
      .catch(() => {
        if (!cancelled) setDetail({ state: 'failed', problem: strings.bridgeError })
      })
    return () => {
      cancelled = true
    }
  }, [id, onSessionEnded])

  // "Wait up to" follows the language's decimal separator (2,5 / 2.5) after a switch too.
  // Only the text changes, so nothing becomes unsaved and undo has nothing new to undo.
  // Adjusted while rendering, as React suggests for state that follows a prop.
  const { language } = useContext(LanguageContext)
  const [shownLanguage, setShownLanguage] = useState(language)
  if (language !== shownLanguage) {
    setShownLanguage(language)
    setHistory((current) => mapHistory(current, (rows) => withTimeoutsIn(rows, strings.locale)))
  }

  // The element list is loaded again each time the place is shown. An element renamed in the
  // Repository meanwhile is renamed in the rows (undo included) and in what counts as saved,
  // since the server renamed the stored steps itself (FR-08); unsaved edits stay.
  const loadedObjects = objects.state === 'loaded' ? objects.objects : undefined
  const [knownObjects, setKnownObjects] = useState(loadedObjects)
  if (loadedObjects && loadedObjects !== knownObjects) {
    setKnownObjects(loadedObjects)
    const renames = knownObjects ? renamedTargets(knownObjects, loadedObjects) : undefined
    if (renames?.size) {
      setHistory((current) => mapHistory(current, (rows) => withRenamedTargets(rows, renames)))
      setSaved((text) => renamedFingerprint(text, renames))
    }
  }

  // On the window, not on the editor: deleting a step removes the button that had the focus,
  // and that is when undo is wanted most. Tests stays mounted while another place is shown.
  useEffect(() => {
    function keyDown(event: globalThis.KeyboardEvent) {
      const command = historyCommand(event)
      const root = editor.current
      if (!command || !root || root.offsetParent === null || mode !== 'view') return
      const target = event.target as Node
      if (target !== globalThis.document.body && !root.contains(target)) return
      event.preventDefault()
      setHistory(command === 'undo' ? undo : redo)
      setServerIssues([])
      setNotice(undefined)
    }
    window.addEventListener('keydown', keyDown)
    return () => window.removeEventListener('keydown', keyDown)
  }, [mode])

  const document = useMemo(() => documentFrom(drafts), [drafts])
  const text = JSON.stringify(document)
  const dirty = detail.state === 'loaded' && text !== saved

  useEffect(() => {
    onDirty(dirty)
  }, [dirty, onDirty])
  useEffect(() => () => onDirty(false), [onDirty])

  // The step schema check runs in the main process (see `src/main/testCases.ts`).
  useEffect(() => {
    let cancelled = false
    window.ayna
      .validateSteps(JSON.parse(text) as StepDocument)
      .then((problems) => {
        if (!cancelled) setSchemaIssues(problems)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [text])

  const problems = unique([
    ...schemaIssues,
    ...localProblems(drafts, objects.state === 'loaded' ? objects.objects : null),
    ...serverIssues.filter((problem) => problem.index < drafts.length),
  ])

  if (detail.state === 'loading') return <p className="hint">{strings.loading}</p>
  if (detail.state === 'failed') {
    return (
      <div className="message message-danger" role="alert">
        <p>{detail.problem}</p>
      </div>
    )
  }
  const { test } = detail

  function edit(next: DraftStep[], typedField?: string) {
    setHistory((current) => record(current, next, typedField))
    setServerIssues([])
    setNotice(undefined)
  }

  function travel(step: typeof undo) {
    setHistory((current) => step(current))
    setServerIssues([])
    setNotice(undefined)
  }

  /** Runs one server call; a failure stays in this mode with the reasons shown. */
  async function run(call: () => Promise<{ ok: true } | TestError>, done: () => void) {
    setBusy(true)
    setErrors([])
    try {
      const result = await call()
      if (result.ok) return done()
      if (result.reason === 'unauthorized') return onSessionEnded()
      setErrors([testErrorText(result)])
      setServerIssues(serverProblems(result.fields ?? []))
    } catch {
      setErrors([strings.bridgeError])
    } finally {
      setBusy(false)
    }
  }

  const first = problems[0]
  const running = live.run?.status === 'running'
  const canSave = dirty && !busy && !first && !running
  const runBlocker = running
    ? null
    : dirty
      ? strings.runNeedsSave
      : drafts.length === 0
        ? strings.runNeedsSteps
        : first
          ? strings.runNeedsFix
          : !version
            ? strings.runNeedsVersion
            : live.agent !== 'connected'
              ? strings.runNeedsAgent
              : null
  // Results belong to the steps that were played: hidden once they are edited.
  const results =
    live.run && !dirty && live.run.stepCount === drafts.length
      ? drafts.map((_, index) => rowState(live.run, index, live.now))
      : null

  function startRun() {
    if (!version) return
    setErrors([])
    setNotice(undefined)
    setStarting(true)
    window.ayna
      .startRun(id, version.id)
      .then((result) => {
        if (result.ok) return
        if (result.reason === 'unauthorized') return onSessionEnded()
        if (result.reason === 'busy' || result.reason === 'agent-not-connected') {
          return setErrors([strings.runStartErrors[result.reason]])
        }
        setErrors([runsErrorText(result)])
      })
      .catch(() => setErrors([strings.bridgeError]))
      .finally(() => setStarting(false))
  }

  function save() {
    if (!canSave) return
    run(
      async () => {
        const result = await window.ayna.saveSteps(id, document)
        if (result.ok) {
          // Show the steps as stored (with their new ids); rows keep their place and focus.
          setDetail({ state: 'loaded', test: result.test })
          setHistory((current) => {
            const stored = draftsFrom(result.test.document, strings.locale).map((draft, i) => ({
              ...draft,
              key: current.present[i]?.key ?? draft.key,
            }))
            const ids = new Map(stored.map((draft) => [draft.key, draft.id]))
            return { ...mapHistory(current, (rows) => withStoredIds(rows, ids)), present: stored }
          })
          setSaved(fingerprint(result.test.document))
        }
        return result
      },
      () => {
        setNotice(strings.testsSaved)
        onChanged()
      },
    )
  }

  function rename(event: FormEvent) {
    event.preventDefault()
    const next = name.trim()
    if (next === test.name) return setMode('view')
    if (!next) return setErrors([strings.testsNameBlank])
    run(
      async () => {
        const result = await window.ayna.renameTest(id, next)
        if (result.ok) setDetail({ state: 'loaded', test: { ...test, name: result.test.name } })
        return result
      },
      () => {
        setMode('view')
        onChanged()
      },
    )
  }

  function remove() {
    run(
      () => window.ayna.deleteTest(id),
      () => onDeleted(test.name),
    )
  }

  function keyDown(event: KeyboardEvent) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault()
      save()
    }
  }

  const errorList = errors.length > 0 && (
    <ul className="message message-danger" role="alert">
      {errors.map((error) => (
        <li key={error}>{error}</li>
      ))}
    </ul>
  )
  const documentProblems = problems.filter((problem) => problem.index < 0)

  return (
    <div className="test-editor" ref={editor} onKeyDown={keyDown}>
      <header className="panel-header">
        {mode === 'rename' ? (
          <form className="inline-form" onSubmit={rename}>
            <label htmlFor="test-rename" className="visually-hidden">
              {strings.testsRenameLabel}
            </label>
            <input
              id="test-rename"
              value={name}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => event.key === 'Escape' && setMode('view')}
              autoFocus
            />
            <button type="submit" className="btn-main" disabled={busy}>
              {strings.testsSave}
            </button>
            <button type="button" onClick={() => setMode('view')} disabled={busy}>
              {strings.testsCancel}
            </button>
          </form>
        ) : (
          <>
            <div className="element-title">
              <h2>
                {test.name}
                {dirty && (
                  <span className="unsaved-dot" title={strings.testsUnsaved}>
                    {' '}
                    ●<span className="visually-hidden">{strings.testsUnsaved}</span>
                  </span>
                )}
              </h2>
              <p className="hint">
                {test.updatedBy
                  ? strings.testsUpdated(
                      test.updatedBy,
                      `${formatDate(test.updatedAt)} ${formatTime(test.updatedAt)}`,
                    )
                  : strings.testsSteps(drafts.length)}
              </p>
            </div>
            <div className="actions">
              <button
                type="button"
                title={strings.testsUndoHint}
                disabled={history.past.length === 0 || running}
                onClick={() => travel(undo)}
              >
                {strings.testsUndo}
              </button>
              <button
                type="button"
                title={strings.testsRedoHint}
                disabled={history.future.length === 0 || running}
                onClick={() => travel(redo)}
              >
                {strings.testsRedo}
              </button>
              <button
                type="button"
                disabled={running}
                onClick={() => {
                  setName(test.name)
                  setErrors([])
                  setMode('rename')
                }}
              >
                {strings.testsRename}
              </button>
              <button
                type="button"
                className="btn-main"
                onClick={save}
                disabled={!canSave}
                title={
                  first ? strings.testsFixFirst(first.index + 1) + ' ' + problemText(first) : ''
                }
              >
                {busy ? strings.testsSaving : strings.testsSave}
              </button>
              <button
                type="button"
                className="btn-main"
                onClick={startRun}
                disabled={running || starting || busy || runBlocker !== null}
                title={runBlocker ?? ''}
              >
                {starting ? strings.runStarting : strings.runRun}
              </button>
            </div>
          </>
        )}
      </header>

      {live.run && (
        <RunBar
          run={live.run}
          now={live.now}
          onStop={() => void window.ayna.stopRun()}
          onChoose={(handle) => void window.ayna.chooseRunWindow(handle)}
          onDetails={() => {
            const runId = live.run!.runId
            window.ayna
              .openReport(runId)
              .then((result) => {
                if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
                if (!result.ok && result.reason !== 'cancelled') setErrors([runsErrorText(result)])
              })
              .catch(() => setErrors([strings.bridgeError]))
          }}
        />
      )}
      {notice && (
        <p className="message message-success" role="status">
          {notice}
        </p>
      )}
      {mode !== 'delete' && errorList}
      {objects.state === 'failed' && (
        <p className="message message-warning">{strings.stepsElementsFailed}</p>
      )}
      {objects.state === 'loaded' && objects.objects.length === 0 && (
        <p className="message message-warning">{strings.stepsNoElements}</p>
      )}
      {documentProblems.length > 0 && (
        <ul className="message message-danger">
          {documentProblems.map((problem) => (
            <li key={`${problem.code} ${problem.message ?? ''}`}>{problemText(problem)}</li>
          ))}
        </ul>
      )}

      <div className="panel-scroll">
        <StepTable
          drafts={drafts}
          problems={problems}
          objects={objects.state === 'loaded' ? objects.objects : null}
          onChange={edit}
          readOnly={running}
          results={results}
        />
      </div>

      <footer className="panel-footer">
        {mode === 'delete' ? (
          <div className="message message-danger">
            <p>{strings.testsDeleteConfirm(test.name)}</p>
            {errorList}
            <div className="form-actions">
              <button type="button" onClick={() => setMode('view')} disabled={busy}>
                {strings.testsCancel}
              </button>
              <button type="button" className="btn-danger" onClick={remove} disabled={busy}>
                {strings.testsDelete}
              </button>
            </div>
          </div>
        ) : (
          <div className="form-actions">
            <button
              type="button"
              className="btn-danger"
              onClick={() => {
                setErrors([])
                setMode('delete')
              }}
            >
              {strings.testsDelete}
            </button>
          </div>
        )}
      </footer>
    </div>
  )
}
