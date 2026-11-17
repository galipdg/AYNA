import { useEffect, useEffectEvent, useState } from 'react'
import type {
  AgentFailure,
  AppVersion,
  Application,
  PickEvent,
  PickHotkeyState,
  ScreenPoint,
  WindowInfo,
} from '../../shared/api.ts'
import { windowDescriptor, type ElementDescriptor } from '../../shared/element.ts'
import { pickState, type PickState } from '../../shared/pick.ts'
import { foldText } from '../../shared/tree.ts'
import {
  buildTree,
  nextSnapshotBudget,
  type Snapshot,
  type TreeNode,
} from '../../shared/snapshot.ts'
import AddToRepository from './AddToRepository.tsx'
import ElementTree from './ElementTree.tsx'
import Page from './Page.tsx'
import PropertyPanel from './PropertyPanel.tsx'
import { controlTypeLabel, formatTime, strings } from './strings.ts'

type List =
  | { state: 'loading' }
  | { state: 'loaded'; windows: WindowInfo[] }
  | { state: 'failed'; reason: AgentFailure; detail?: string }

async function fetchWindows(): Promise<List> {
  try {
    const result = await window.ayna.listWindows()
    return result.ok
      ? { state: 'loaded', windows: result.windows }
      : { state: 'failed', reason: result.reason, detail: result.detail }
  } catch {
    return { state: 'failed', reason: 'not-connected' }
  }
}

/**
 * A capture of the chosen window. `budgetMs` is the walk budget sent to the agent (undefined:
 * its default); a window that once needed a longer one keeps it for the next capture.
 */
type Capture = { budgetMs?: number } & (
  | { state: 'loading' }
  | { state: 'loaded'; snapshot: Snapshot; root: TreeNode }
  | { state: 'failed'; reason: AgentFailure; detail?: string }
)

async function fetchSnapshot(handle: number, budgetMs?: number): Promise<Capture> {
  try {
    const result = await window.ayna.snapshot(handle, budgetMs)
    if (!result.ok) {
      return { state: 'failed', reason: result.reason, detail: result.detail, budgetMs }
    }
    const root = buildTree(result.snapshot.elements)
    return root
      ? { state: 'loaded', snapshot: result.snapshot, root, budgetMs }
      : { state: 'failed', reason: 'bad-response', budgetMs }
  } catch {
    return { state: 'failed', reason: 'not-connected', budgetMs }
  }
}

/** The budget "Capture again" sends: a longer one after the walk ran out of time (#204). */
function retryBudget(capture: Capture | undefined): number | undefined {
  if (capture?.state === 'failed' && capture.reason === 'snapshot-timeout') {
    return nextSnapshotBudget(capture.budgetMs)
  }
  return capture?.budgetMs
}

const seconds = (ms: number) => Math.round(ms / 1000)

function capturedLine({ capture, app }: Snapshot): string {
  const time = formatTime(capture.startedAt)
  const exe = app.exeName && [app.exeName, app.fileVersion].filter(Boolean).join(' ')
  return strings.spyCaptured(time, exe, capture.elementCount, capture.durationMs)
}

function processLabel(win: WindowInfo): string {
  const name = win.processName ?? strings.spyUnknownProcess
  return win.processId === null ? name : `${name} · ${win.processId}`
}

/** The last press of the pick key; `gone`: the window to capture has closed since. */
type Pick = { point: ScreenPoint; state: PickState | { state: 'gone' } }

/** What the last pick found, in one line for the tree panel's footer. */
function PickNote({
  pick,
  onCapture,
  onCaptureAgain,
}: {
  pick: Pick
  onCapture: (handle: number) => void
  onCaptureAgain: () => void
}) {
  const { point, state } = pick
  switch (state.state) {
    case 'element':
      return (
        <p className="hint" role="status">
          {strings.spyPicked(point.x, point.y)}
        </p>
      )
    case 'not-captured':
      return (
        <div className="message message-warning" role="status">
          <span>{strings.spyPickNotCaptured(point.x, point.y)}</span>
          <button type="button" onClick={() => onCapture(state.handle)}>
            {strings.spyPickCapture}
          </button>
        </div>
      )
    case 'changed':
      return (
        <div className="message message-warning" role="status">
          <span>{strings.spyPickChanged}</span>
          <button type="button" onClick={onCaptureAgain}>
            {strings.spyCaptureAgain}
          </button>
        </div>
      )
    case 'own-window':
      return (
        <p className="hint" role="status">
          {strings.spyPickOwnWindow}
        </p>
      )
    case 'no-window':
      return (
        <p className="hint" role="status">
          {strings.spyPickNoWindow(point.x, point.y)}
        </p>
      )
    case 'gone':
      return (
        <p className="message message-warning" role="status">
          {strings.spyPickGone}
        </p>
      )
    case 'failed':
      return (
        <p className="message message-danger" role="alert">
          {strings.agentErrors[state.reason](state.detail)}
        </p>
      )
  }
}

/** The chosen element in one line: its text (or AutomationId) and its type in plain words. */
function ElementTitle({ element }: { element: ElementDescriptor }) {
  const { name, automationId, controlType, windowTitle } = element
  return (
    <div className="element-title">
      <h2>
        {name ?? automationId ?? strings.spyNoName}{' '}
        <span className="node-type">{controlTypeLabel(controlType)}</span>
      </h2>
      {windowTitle && controlType !== 'Window' && (
        <p className="hint">{strings.spyInWindow(windowTitle)}</p>
      )}
    </div>
  )
}

/**
 * Three panels side by side (#184): windows | element tree | properties. Lists the desktop's
 * top-level windows; choosing one flashes a frame around it on screen
 * and captures its element tree. Choosing an element in the tree frames it and shows its
 * properties; "Add to repository" stores it in `app`, under the version chosen in the top
 * bar (#25, #183).
 */
export default function ObjectSpy({ app, version }: { app: Application; version?: AppVersion }) {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [selected, setSelected] = useState<WindowInfo>()
  const [hotkey, setHotkey] = useState<PickHotkeyState>()
  const [pick, setPick] = useState<Pick>()
  const [capture, setCapture] = useState<Capture>()
  const [node, setNode] = useState<TreeNode>()
  const [adding, setAdding] = useState(false)
  const [saved, setSaved] = useState<string>()
  const [windowQuery, setWindowQuery] = useState('')
  const [advancedOpen, setAdvancedOpen] = useState(false)

  // Entering `loading` (first render, Refresh, agent reconnected) fetches the list.
  const loading = list.state === 'loading'
  useEffect(() => {
    if (!loading) return
    let cancelled = false
    fetchWindows().then((next) => {
      if (cancelled) return
      setList(next)
      // Handles die with their window; keep the choice only if it is still listed.
      setSelected((current) =>
        next.state === 'loaded' && current
          ? next.windows.find((win) => win.handle === current.handle)
          : undefined,
      )
    })
    return () => {
      cancelled = true
    }
  }, [loading])

  // Entering `loading` (window chosen, Capture again, agent reconnected) captures the
  // selected window; choosing another window meanwhile drops the older answer.
  const capturing = capture?.state === 'loading'
  const budgetMs = capture?.budgetMs
  const handle = selected?.handle
  useEffect(() => {
    if (!capturing || handle === undefined) return
    let cancelled = false
    fetchSnapshot(handle, budgetMs).then((next) => {
      if (cancelled) return
      setCapture(next)
      // The window's own element first, so the panel shows its full descriptor.
      if (next.state === 'loaded') setNode(next.root)
    })
    return () => {
      cancelled = true
    }
  }, [capturing, handle, budgetMs])

  useEffect(() => {
    // A list that failed because the agent was down is fetched again once it connects.
    const unsubscribe = window.ayna.onAgentStatus((status) => {
      if (status.state !== 'connected') return
      setList((current) =>
        current.state === 'failed' && current.reason === 'not-connected'
          ? { state: 'loading' }
          : current,
      )
      setCapture((current) =>
        current?.state === 'failed' && current.reason === 'not-connected'
          ? { state: 'loading', budgetMs: current.budgetMs }
          : current,
      )
    })
    return () => {
      unsubscribe()
      window.ayna.highlight(null)
    }
  }, [])

  // A pick is read against the capture on screen when the key is pressed (#24).
  const onPick = useEffectEvent((event: PickEvent) => {
    const shown =
      capture?.state === 'loaded'
        ? { snapshotId: capture.snapshot.snapshotId, root: capture.root }
        : undefined
    const state = pickState(event, shown)
    if (state.state === 'element') chooseNode(state.node)
    setPick({ point: event.point, state })
  })

  // The pick key is global, so it is held only while the Spy is on screen.
  useEffect(() => {
    let cancelled = false
    const unsubscribe = window.ayna.onPick((event) => onPick(event))
    window.ayna.setPickHotkey(true).then((state) => !cancelled && setHotkey(state))
    return () => {
      cancelled = true
      unsubscribe()
      window.ayna.setPickHotkey(false)
    }
  }, [])

  function choose(win: WindowInfo) {
    setSelected(win)
    window.ayna.highlight(win.bounds)
    startCapture(undefined)
  }

  /** "Capture this window" after a pick: the window may be newer than the list on screen. */
  async function captureWindow(handle: number, point: ScreenPoint) {
    let win = list.state === 'loaded' ? list.windows.find((w) => w.handle === handle) : undefined
    if (!win) {
      const next = await fetchWindows()
      setList(next)
      win = next.state === 'loaded' ? next.windows.find((w) => w.handle === handle) : undefined
    }
    if (win) choose(win)
    else setPick({ point, state: { state: 'gone' } })
  }

  function startCapture(budgetMs: number | undefined) {
    setCapture({ state: 'loading', budgetMs })
    // A pick note about the window that was on screen is out of date once it is captured anew.
    setPick(undefined)
    setNode(undefined)
    setAdding(false)
    setSaved(undefined)
  }

  function chooseNode(next: TreeNode) {
    setNode(next)
    setSaved(undefined)
    setPick(undefined) // a pick sets its own note right after
    window.ayna.highlight(next.element.bounds ?? null)
  }

  const windows =
    list.state === 'loaded'
      ? list.windows.filter((win) =>
          foldText(`${win.title} ${win.processName ?? ''}`).includes(foldText(windowQuery.trim())),
        )
      : []
  const element = capture?.state === 'loaded' && node ? node.element : undefined
  return (
    <Page title={strings.spyTitle} help={strings.pageHelp.spy}>
      <div className="spy">
        <section className="panel spy-panel" aria-label={strings.spyWindowsTitle}>
          <header className="panel-header">
            <h2>{strings.spyWindowsTitle}</h2>
            <button type="button" onClick={() => setList({ state: 'loading' })} disabled={loading}>
              {strings.spyRefresh}
            </button>
          </header>
          {list.state === 'loaded' && list.windows.length > 0 && (
            <input
              type="search"
              aria-label={strings.spySearchWindows}
              placeholder={strings.spySearchWindows}
              value={windowQuery}
              onChange={(event) => setWindowQuery(event.target.value)}
            />
          )}
          <div className="panel-scroll">
            {loading && <p className="hint">{strings.loading}</p>}
            {list.state === 'failed' && (
              <p className="message message-danger" role="alert">
                {strings.agentErrors[list.reason](list.detail)}
              </p>
            )}
            {list.state === 'loaded' && list.windows.length === 0 && (
              <div className="empty">
                <p className="empty-title">{strings.spyEmpty}</p>
              </div>
            )}
            {list.state === 'loaded' && list.windows.length > 0 && windows.length === 0 && (
              <p className="hint">{strings.spyNoWindowMatch(windowQuery.trim())}</p>
            )}
            <ul className="choice-list">
              {windows.map((win) => (
                <li key={win.handle}>
                  <button
                    type="button"
                    className={win.handle === selected?.handle ? 'selected two-line' : 'two-line'}
                    aria-pressed={win.handle === selected?.handle}
                    title={win.title}
                    onClick={() => choose(win)}
                  >
                    <span>{win.title || strings.spyNoTitle}</span>
                    <span className="hint">{processLabel(win)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel spy-panel" aria-label={strings.spyTreeTitle}>
          <header className="panel-header">
            <h2>{selected ? selected.title || strings.spyNoTitle : strings.spyTreeTitle}</h2>
            {selected && (
              <button
                type="button"
                onClick={() => startCapture(retryBudget(capture))}
                disabled={capturing}
              >
                {strings.spyCaptureAgain}
              </button>
            )}
          </header>
          {!selected && (
            <div className="empty">
              <p className="empty-title">{strings.spyChooseWindow}</p>
            </div>
          )}
          {capturing && (
            <p className="hint">
              {budgetMs === undefined
                ? strings.spyCapturing
                : strings.spyCapturingLonger(seconds(budgetMs))}
            </p>
          )}
          {capture?.state === 'failed' && (
            <p className="message message-danger" role="alert">
              {strings.agentErrors[capture.reason](capture.detail)}
              {capture.reason === 'snapshot-timeout' &&
                ` ${strings.spyCaptureLonger(seconds(nextSnapshotBudget(capture.budgetMs)))}`}
            </p>
          )}
          {selected && capture?.state === 'loaded' && (
            <>
              {!!capture.snapshot.capture.readErrors && (
                <p className="message message-warning">
                  {strings.spyReadErrors(capture.snapshot.capture.readErrors)}
                </p>
              )}
              <ElementTree
                key={capture.snapshot.snapshotId}
                root={capture.root}
                selectedId={node?.id}
                onSelect={chooseNode}
              />
              <p className="hint">{capturedLine(capture.snapshot)}</p>
            </>
          )}
          <footer className="panel-footer">
            {hotkey && (
              <p className={hotkey.active ? 'hint' : 'field-error'}>
                {hotkey.active
                  ? strings.spyHotkeyHint(hotkey.label)
                  : strings.spyHotkeyTaken(hotkey.label)}
              </p>
            )}
            {pick && (
              <PickNote
                pick={pick}
                onCapture={(windowHandle) => captureWindow(windowHandle, pick.point)}
                onCaptureAgain={() => startCapture(retryBudget(capture))}
              />
            )}
          </footer>
        </section>

        <section className="panel spy-panel" aria-label={strings.spyPropertiesTitle}>
          {!selected && (
            <div className="empty">
              <p className="empty-title">{strings.spyChooseElement}</p>
            </div>
          )}
          {selected && element && node && capture?.state === 'loaded' && adding && (
            <AddToRepository
              // Another element or capture starts a fresh form.
              key={`${capture.snapshot.snapshotId}/${node.id}`}
              app={app}
              snapshot={capture.snapshot}
              node={node}
              version={version}
              onSaved={(object) => {
                setAdding(false)
                setSaved(object.name)
              }}
              onCancel={() => setAdding(false)}
            />
          )}
          {selected && element && !adding && (
            <>
              <header className="panel-header">
                <ElementTitle element={element} />
              </header>
              <div className="panel-scroll">
                {saved && (
                  <p className="message message-success" role="status">
                    {strings.repoSaved(saved)}
                  </p>
                )}
                <PropertyPanel
                  element={element}
                  advancedOpen={advancedOpen}
                  onAdvancedToggle={setAdvancedOpen}
                />
              </div>
              <footer className="panel-footer form-actions">
                <button type="button" className="btn-main" onClick={() => setAdding(true)}>
                  {strings.repoAdd}
                </button>
              </footer>
            </>
          )}
          {selected && !element && (
            <>
              <header className="panel-header">
                <ElementTitle element={windowDescriptor(selected)} />
              </header>
              <div className="panel-scroll">
                <PropertyPanel
                  element={windowDescriptor(selected)}
                  note={capture?.state === 'failed' ? strings.spyWindowOnly : undefined}
                  advancedOpen={advancedOpen}
                  onAdvancedToggle={setAdvancedOpen}
                />
              </div>
            </>
          )}
        </section>
      </div>
    </Page>
  )
}
