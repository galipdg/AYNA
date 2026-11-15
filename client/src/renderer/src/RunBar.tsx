// The bar above the steps while and after a test runs (#44, wireframe 8).

import { useEffect, useState } from 'react'
import type { AgentState } from '../../shared/api.ts'
import { runBarState, type LiveRun } from '../../shared/liveRun.ts'
import { formatDuration, serverText, strings } from './strings.ts'

export default function RunBar({
  run,
  now,
  onStop,
  onChoose,
  onDetails,
}: {
  run: LiveRun
  /** Wall-clock time, ticked by the editor while the run plays. */
  now: number
  onStop: () => void
  onChoose: (handle: number | null) => void
  onDetails: () => void
}) {
  const bar = runBarState(run, now)
  const details = (
    <button type="button" onClick={onDetails}>
      {strings.runDetails}
    </button>
  )
  const stop = run.mine && (
    <button type="button" onClick={onStop}>
      {strings.runStop}
    </button>
  )
  const tone = {
    running: 'message-info',
    choosing: 'message-warning',
    passed: 'message-success',
    failed: 'message-danger',
    aborted: 'message-warning',
  }[bar.kind]

  let text: string
  if (bar.kind === 'running') {
    text = run.mine
      ? strings.runRunning(bar.stepNumber, run.stepCount, formatDuration(bar.elapsedMs))
      : strings.runRunningBy(run.startedBy, bar.stepNumber, run.stepCount)
  } else if (bar.kind === 'choosing') {
    text = strings.runChooseWindow(run.choosing?.title ?? null)
  } else if (bar.kind === 'passed') {
    text = `✓ ${strings.runPassed}`
  } else if (bar.kind === 'failed') {
    const category = bar.failed?.category
    const parts = [
      `✕ ${strings.runFailedAt(bar.stepNumber)}`,
      category ? (strings.runCategories[category] ?? category) : null,
      bar.failed?.message ? serverText(bar.failed.message) : null,
    ]
    text = parts.filter(Boolean).join(' · ')
  } else {
    text = strings.runStoppedAt(bar.stepNumber)
  }

  return (
    <>
      <div className={`message run-bar ${tone}`} role="status">
        <span>{text}</span>
        <span className="run-bar-actions">
          {bar.kind === 'choosing' &&
            run.mine &&
            run.choosing?.windows.map((window) => (
              <button key={window.handle} type="button" onClick={() => onChoose(window.handle)}>
                {window.title || window.className}
                {window.processName ? ` (${window.processName})` : ''}
              </button>
            ))}
          {(bar.kind === 'running' || bar.kind === 'choosing') && stop}
          {bar.kind !== 'running' && bar.kind !== 'choosing' && details}
        </span>
      </div>
      {run.problem === 'not-stored' && (
        <p className="message message-warning">{strings.runNotStored}</p>
      )}
    </>
  )
}

/**
 * The run shown for `testId`: this client's run of it, or the newest one another client is
 * running; plus the agent's state (Run needs it) and a clock that ticks while a run plays.
 */
export function useLiveRun(testId: string): { run: LiveRun | null; agent: AgentState; now: number } {
  const [run, setRun] = useState<LiveRun | null>(null)
  const [agent, setAgent] = useState<AgentState>('starting')
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    // The editor is keyed by test, so `testId` is fixed for the life of this hook.
    let cancelled = false
    const off = window.ayna.onRun((next) => {
      if (next.testId !== testId) return
      setRun((shown) => (shows(shown, next) ? next : shown))
    })
    window.ayna
      .watchRuns(testId)
      .then((mine) => {
        if (!cancelled && mine) setRun((shown) => (shows(shown, mine) ? mine : shown))
      })
      .catch(() => {})
    return () => {
      cancelled = true
      off()
      void window.ayna.watchRuns(null).catch(() => {})
    }
  }, [testId])

  useEffect(() => {
    let cancelled = false
    const off = window.ayna.onAgentStatus((status) => setAgent(status.state))
    window.ayna
      .getAgentStatus()
      .then((status) => !cancelled && setAgent(status.state))
      .catch(() => {})
    return () => {
      cancelled = true
      off()
    }
  }, [])

  const playing = run?.status === 'running'
  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [playing])

  return { run, agent, now }
}

/** Whether `next` replaces the run on screen: the same run, a newer one, or one that is playing. */
function shows(shown: LiveRun | null, next: LiveRun): boolean {
  if (!shown || shown.runId === next.runId) return true
  if (shown.status === 'running' && shown.mine) return false
  return next.status === 'running' || Date.parse(next.startedAt) >= Date.parse(shown.startedAt)
}
