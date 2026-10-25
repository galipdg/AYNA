import { useEffect, useState } from 'react'
import { ayna } from './ayna.js'
import { strings } from './strings.js'

/** @typedef {import('../../shared/api.js').AppInfo} AppInfo */

export default function App() {
  const [info, setInfo] = useState(/** @type {AppInfo | null} */ (null))
  const [error, setError] = useState(false)

  useEffect(() => {
    ayna.getAppInfo().then(setInfo, () => setError(true))
  }, [])

  return (
    <main className="app">
      <h1>{strings.appName}</h1>
      <p className="tagline">{strings.tagline}</p>
      <section className="card">
        <h2>{strings.versionsTitle}</h2>
        {error && <p className="error">{strings.bridgeError}</p>}
        {!error && !info && <p>{strings.loading}</p>}
        {info && (
          <dl>
            <dt>App</dt>
            <dd>
              {info.name} {info.version}
            </dd>
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
      </section>
    </main>
  )
}
