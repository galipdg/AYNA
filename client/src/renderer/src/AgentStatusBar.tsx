import { useEffect, useState } from 'react'
import type { AgentState, AgentStatus } from '../../shared/api.ts'
import Menu from './Menu.tsx'
import { strings } from './strings.ts'

const tone: Record<AgentState, string> = {
  starting: 'accent',
  connected: 'success',
  restarting: 'warning',
  failed: 'danger',
  stopped: 'muted',
}

/** The local agent's state (FR-05), kept current from the main process. */
export function useAgentStatus(): AgentStatus | null {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  useEffect(() => {
    // Subscribe first, so a change between the two calls is not lost.
    const unsubscribe = window.ayna.onAgentStatus(setStatus)
    window.ayna.getAgentStatus().then((current) => setStatus((seen) => seen ?? current))
    return unsubscribe
  }, [])
  return status
}

/** "● Agent ready" and its siblings, as a status pill. */
export function AgentPill({ status }: { status: AgentStatus }) {
  const { state, restarts, maxRestarts } = status
  return (
    <span className={`pill pill-${tone[state]}`}>
      <span className="dot" aria-hidden="true" />
      {strings.agentStates[state]}
      {state === 'restarting' && ` (${strings.agentAttempt(restarts, maxRestarts)})`}
    </span>
  )
}

/** The agent's details and "Start again" once it has failed. */
export function AgentDetails({ status }: { status: AgentStatus }) {
  return (
    <>
      {status.state === 'failed' && status.detail && (
        <p className="hint agent-detail">{status.detail}</p>
      )}
      {status.state === 'failed' && (
        <button type="button" className="btn-main" onClick={() => window.ayna.retryAgent()}>
          {strings.agentRetry}
        </button>
      )}
    </>
  )
}

/** The top bar's agent indicator; a click shows the details. */
export default function AgentStatusBar() {
  const status = useAgentStatus()
  if (!status) return null
  return (
    <Menu
      title={strings.agentLabel}
      className="menu-plain"
      align="end"
      label={<AgentPill status={status} />}
    >
      {() => (
        <div className="menu-body">
          <p className="menu-title">{strings.agentLabel}</p>
          <p className="hint">{strings.settingsAgentHint}</p>
          <p role="status">
            <AgentPill status={status} />
          </p>
          <AgentDetails status={status} />
        </div>
      )}
    </Menu>
  )
}
