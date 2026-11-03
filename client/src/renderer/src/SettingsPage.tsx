import { useEffect, useState } from 'react'
import type { AppInfo } from '../../shared/api.ts'
import { AgentDetails, AgentPill, useAgentStatus } from './AgentStatusBar.tsx'
import Page from './Page.tsx'
import { strings } from './strings.ts'

/** This computer's connection to AYNA: server, language, agent, and the runtime versions. */
export default function SettingsPage({
  url,
  onChangeServer,
}: {
  url: string
  onChangeServer: () => void
}) {
  const [info, setInfo] = useState<AppInfo>()
  const [infoFailed, setInfoFailed] = useState(false)
  const agent = useAgentStatus()

  useEffect(() => {
    window.ayna.getAppInfo().then(setInfo, () => setInfoFailed(true))
  }, [])

  return (
    <Page title={strings.nav.settings} help={strings.pageHelp.settings}>
      <div className="panel settings">
        <div className="setting">
          <span className="setting-name">{strings.settingsServer}</span>
          <span>{strings.settingsConnected(url)}</span>
          <button type="button" onClick={onChangeServer}>
            {strings.changeServer}
          </button>
        </div>
        <div className="setting">
          <span className="setting-name">{strings.settingsLanguage}</span>
          <span>{strings.topLanguage}</span>
          <span className="hint">{strings.topLanguageHint}</span>
        </div>
        <div className="setting">
          <span className="setting-name" title={strings.settingsAgentHint}>
            {strings.settingsAgent}
          </span>
          <span>{agent && <AgentPill status={agent} />}</span>
          <span>{agent && <AgentDetails status={agent} />}</span>
        </div>
        <details className="advanced">
          <summary>{strings.versionsTitle}</summary>
          {infoFailed && <p className="field-error">{strings.bridgeError}</p>}
          {!infoFailed && !info && <p className="hint">{strings.loading}</p>}
          {info && (
            <dl className="facts">
              <dt>AYNA</dt>
              <dd>{info.version}</dd>
              <dt>Electron</dt>
              <dd>{info.electron}</dd>
              <dt>Chromium</dt>
              <dd>{info.chrome}</dd>
              <dt>Node</dt>
              <dd>{info.node}</dd>
              <dt>Platform</dt>
              <dd>{info.platform}</dd>
            </dl>
          )}
        </details>
      </div>
    </Page>
  )
}
