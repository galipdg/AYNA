import { useEffect, useState } from 'react'
import type { AgentStatus } from '../../shared/api.ts'
import { strings } from './strings.ts'

const tone = { connected: 'ok', failed: 'error' } as const

/** One line showing whether the local agent is connected; offers a retry once it has failed. */
export default function AgentStatusBar() {
  const [status, setStatus] = useState<AgentStatus | null>(null)

  useEffect(() => {
    // Subscribe first, so a change between the two calls is not lost.
    const unsubscribe = window.ayna.onAgentStatus(setStatus)
    window.ayna.getAgentStatus().then((current) => setStatus((seen) => seen ?? current))
    return unsubscribe
  }, [])

  if (!status) return null
  const { state, restarts, maxRestarts, detail } = status
  return (
    <p className="agent-status" role="status">
      {strings.agentLabel}:{' '}
      <span className={state in tone ? tone[state as keyof typeof tone] : undefined}>
        {strings.agentStates[state]}
      </span>
      {state === 'restarting' && ` (${strings.agentAttempt(restarts, maxRestarts)})`}
      {state === 'failed' && (
        <>
          {detail && <span className="agent-detail"> — {detail}</span>}{' '}
          <button type="button" onClick={() => window.ayna.retryAgent()}>
            {strings.agentRetry}
          </button>
        </>
      )}
    </p>
  )
}
