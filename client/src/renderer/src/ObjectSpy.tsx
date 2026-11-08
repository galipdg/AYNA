import { useEffect, useState } from 'react'
import type {
  AgentFailure,
  AppVersion,
  Application,
  PickHotkeyState,
  ScreenPoint,
  WindowInfo,
} from '../../shared/api.ts'
import { windowDescriptor, type ElementDescriptor } from '../../shared/element.ts'
import { foldText } from '../../shared/tree.ts'
import { buildTree, type Snapshot, type TreeNode } from '../../shared/snapshot.ts'
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

type Capture =
  | { state: 'loading' }
  | { state: 'loaded'; snapshot: Snapshot; root: TreeNode }
  | { state: 'failed'; reason: AgentFailure; detail?: string }

async function fetchSnapshot(handle: number): Promise<Capture> {
  try {
    const result = await window.ayna.snapshot(handle)
    if (!result.ok) return { state: 'failed', reason: result.reason, detail: result.detail }
    const root = buildTree(result.snapshot.elements)
    return root
      ? { state: 'loaded', snapshot: result.snapshot, root }
      : { state: 'failed', reason: 'bad-response' }
  } catch {
    return { state: 'failed', reason: 'not-connected' }
  }
}

function capturedLine({ capture, app }: Snapshot): string {
  const time = formatTime(capture.startedAt)
  const exe = app.exeName && [app.exeName, app.fileVersion].filter(Boolean).join(' ')
  return strings.spyCaptured(time, exe, capture.elementCount, capture.durationMs)
}

function processLabel(win: WindowInfo): string {
  return `${win.processName ?? strings.spyUnknownProcess} · ${win.processId}`
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
  const [picked, setPicked] = useState<ScreenPoint>()
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
  const handle = selected?.handle
  useEffect(() => {
    if (!capturing || handle === undefined) return
    let cancelled = false
    fetchSnapshot(handle).then((next) => {
      if (cancelled) return
      setCapture(next)
      // The window's own element first, so the panel shows its full descriptor.
      if (next.state === 'loaded') setNode(next.root)
    })
    return () => {
      cancelled = true
    }
  }, [capturing, handle])

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
          ? { state: 'loading' }
          : current,
      )
    })
    return () => {
      unsubscribe()
      window.ayna.highlight(null)
    }
  }, [])

  // The pick key is global, so it is held only while the Spy is on screen.
  useEffect(() => {
    let cancelled = false
    const unsubscribe = window.ayna.onPick(setPicked)
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
    captureAgain()
  }

  function captureAgain() {
    setCapture({ state: 'loading' })
    setNode(undefined)
    setAdding(false)
    setSaved(undefined)
  }

  function chooseNode(next: TreeNode) {
    setNode(next)
    setSaved(undefined)
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
              <button type="button" onClick={captureAgain} disabled={capturing}>
                {strings.spyCaptureAgain}
              </button>
            )}
          </header>
          {!selected && (
            <div className="empty">
              <p className="empty-title">{strings.spyChooseWindow}</p>
            </div>
          )}
          {capturing && <p className="hint">{strings.spyCapturing}</p>}
          {capture?.state === 'failed' && (
            <p className="message message-danger" role="alert">
              {strings.agentErrors[capture.reason](capture.detail)}
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
            {picked && (
              <p className="hint" role="status">
                {strings.spyPicked(picked.x, picked.y)}
              </p>
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
