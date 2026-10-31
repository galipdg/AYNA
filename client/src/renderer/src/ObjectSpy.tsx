import { useEffect, useState } from 'react'
import type { AgentFailure, WindowInfo } from '../../shared/api.ts'
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

function processLabel(win: WindowInfo): string {
  return `${win.processName ?? strings.spyUnknownProcess} · ${win.processId}`
}

/** Lists the desktop's top-level windows; choosing one flashes a frame around it on screen. */
export default function ObjectSpy() {
  const [list, setList] = useState<List>({ state: 'loading' })
  const [selected, setSelected] = useState<WindowInfo>()

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

  useEffect(() => {
    // A list that failed because the agent was down is fetched again once it connects.
    const unsubscribe = window.ayna.onAgentStatus((status) => {
      if (status.state !== 'connected') return
      setList((current) =>
        current.state === 'failed' && current.reason === 'not-connected'
          ? { state: 'loading' }
          : current,
      )
    })
    return () => {
      unsubscribe()
      window.ayna.highlight(null)
    }
  }, [])

  function choose(win: WindowInfo) {
    setSelected(win)
    window.ayna.highlight(win.bounds)
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
      {selected && (
        <dl>
          <dt>{strings.spyFields.title}</dt>
          <dd>{selected.title || strings.spyNoTitle}</dd>
          <dt>{strings.spyFields.className}</dt>
          <dd>{selected.className}</dd>
          <dt>{strings.spyFields.process}</dt>
          <dd>{processLabel(selected)}</dd>
          <dt>{strings.spyFields.handle}</dt>
          <dd>{selected.handle}</dd>
          <dt>{strings.spyFields.bounds}</dt>
          <dd>{selected.bounds.join(', ')}</dd>
        </dl>
      )}
      <p className="spy-pending">{strings.spyTreePending}</p>
    </section>
  )
}
