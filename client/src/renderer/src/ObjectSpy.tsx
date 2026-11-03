import { useEffect, useState } from 'react'
import type { AgentFailure, PickHotkeyState, ScreenPoint, WindowInfo } from '../../shared/api.ts'
import { windowDescriptor } from '../../shared/element.ts'
import { buildTree, type Snapshot, type TreeNode } from '../../shared/snapshot.ts'
import ElementTree from './ElementTree.tsx'
import PropertyPanel from './PropertyPanel.tsx'
import { strings } from './strings.ts'

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
  const time = new Date(capture.startedAt).toLocaleTimeString()
  const exe = app.exeName && [app.exeName, app.fileVersion].filter(Boolean).join(' ')
  return strings.spyCaptured(time, exe, capture.elementCount, capture.durationMs)
}

function processLabel(win: WindowInfo): string {
  return `${win.processName ?? strings.spyUnknownProcess} · ${win.processId}`
}

/**
 * Lists the desktop's top-level windows; choosing one flashes a frame around it on screen
 * and captures its element tree. Choosing an element in the tree frames it and shows its
 * properties.
 */
export default function ObjectSpy() {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [selected, setSelected] = useState<WindowInfo>()
  const [hotkey, setHotkey] = useState<PickHotkeyState>()
  const [picked, setPicked] = useState<ScreenPoint>()
  const [capture, setCapture] = useState<Capture>()
  const [node, setNode] = useState<TreeNode>()

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
  }

  function chooseNode(next: TreeNode) {
    setNode(next)
    window.ayna.highlight(next.element.bounds ?? null)
  }

  return (
    <section className="card spy">
      <div className="spy-header">
        <h2>{strings.spyTitle}</h2>
        <button type="button" onClick={() => setList({ state: 'loading' })} disabled={loading}>
          {strings.spyRefresh}
        </button>
      </div>
      {loading && <p>{strings.loading}</p>}
      {list.state === 'failed' && (
        <p className="error">{strings.agentErrors[list.reason](list.detail)}</p>
      )}
      {list.state === 'loaded' && list.windows.length === 0 && <p>{strings.spyEmpty}</p>}
      {list.state === 'loaded' && list.windows.length > 0 && (
        <>
          <p>{strings.spyIntro}</p>
          <ul className="app-list">
            {list.windows.map((win) => (
              <li key={win.handle}>
                <button
                  type="button"
                  className={win.handle === selected?.handle ? 'selected' : undefined}
                  aria-pressed={win.handle === selected?.handle}
                  onClick={() => choose(win)}
                >
                  <span>{win.title || strings.spyNoTitle}</span>
                  <span className="technology">{processLabel(win)}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {selected && capture && (
        <section className="spy-elements" aria-label={strings.spyTreeTitle}>
          <div className="spy-header">
            <h3>{strings.spyTreeTitle}</h3>
            <button type="button" onClick={captureAgain} disabled={capturing}>
              {strings.spyCaptureAgain}
            </button>
          </div>
          {capturing && <p>{strings.spyCapturing}</p>}
          {capture.state === 'failed' && (
            <p className="error">{strings.agentErrors[capture.reason](capture.detail)}</p>
          )}
          {capture.state === 'loaded' && (
            <>
              <p className="spy-pending">{capturedLine(capture.snapshot)}</p>
              {!!capture.snapshot.capture.readErrors && (
                <p className="spy-pending">
                  {strings.spyReadErrors(capture.snapshot.capture.readErrors)}
                </p>
              )}
              <ElementTree
                key={capture.snapshot.snapshotId}
                root={capture.root}
                selectedId={node?.id}
                onSelect={chooseNode}
              />
            </>
          )}
        </section>
      )}
      {selected &&
        (capture?.state === 'loaded' && node ? (
          <PropertyPanel element={node.element} />
        ) : (
          <PropertyPanel
            element={windowDescriptor(selected)}
            note={capture?.state === 'failed' ? strings.spyWindowOnly : undefined}
          />
        ))}
      {hotkey && (
        <p className={hotkey.active ? 'spy-pending' : 'error'}>
          {hotkey.active
            ? strings.spyHotkeyHint(hotkey.label)
            : strings.spyHotkeyTaken(hotkey.label)}
        </p>
      )}
      {picked && <p role="status">{strings.spyPicked(picked.x, picked.y)}</p>}
    </section>
  )
}
