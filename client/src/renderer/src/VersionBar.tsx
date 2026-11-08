import { useEffect, useState, type FormEvent } from 'react'
import type { AppVersion } from '../../shared/api.ts'
import { strings } from './strings.ts'

type Versions =
  | { state: 'loading' }
  | { state: 'loaded'; versions: AppVersion[] }
  | { state: 'failed'; message: string }

/**
 * The application version the Spy saves captures and repository objects under: chosen once
 * here, not in each form. Without versions it asks for the one being tested.
 */
export default function VersionBar({
  appId,
  versionId,
  onChange,
}: {
  appId: string
  versionId?: string
  onChange: (versionId: string) => void
}) {
  const [versions, setVersions] = useState<Versions>({ state: 'loading' })
  const [adding, setAdding] = useState(false)
  const [newVersion, setNewVersion] = useState('')
  const [error, setError] = useState<string>()

  const loading = versions.state === 'loading'
  useEffect(() => {
    if (!loading) return
    let cancelled = false
    window.ayna.listVersions(appId).then(
      (result) => {
        if (cancelled) return
        if (!result.ok) {
          return setVersions({ state: 'failed', message: strings.versionErrors[result.reason] })
        }
        setVersions({ state: 'loaded', versions: result.versions })
        // Keep the choice if it still exists; otherwise the newest-listed version.
        const kept = result.versions.find((version) => version.id === versionId)
        const newest = result.versions.at(-1)
        if (!kept && newest) onChange(newest.id)
      },
      () => !cancelled && setVersions({ state: 'failed', message: strings.bridgeError }),
    )
    return () => {
      cancelled = true
    }
  }, [loading, appId, versionId, onChange])

  async function add(event: FormEvent) {
    event.preventDefault()
    setError(undefined)
    const version = newVersion.trim()
    if (!version) return setError(strings.versionErrors.invalid)
    try {
      const result = await window.ayna.createVersion(appId, version)
      if (!result.ok) return setError(result.detail ?? strings.versionErrors[result.reason])
      setNewVersion('')
      setAdding(false)
      onChange(result.version.id)
      setVersions({ state: 'loading' })
    } catch {
      setError(strings.bridgeError)
    }
  }

  if (versions.state === 'loading') return <p className="version-bar">{strings.loading}</p>
  if (versions.state === 'failed') {
    return (
      <div className="version-bar">
        <p className="error" role="alert">
          {versions.message}
        </p>
        <button type="button" onClick={() => setVersions({ state: 'loading' })}>
          {strings.versionRetry}
        </button>
      </div>
    )
  }

  const none = versions.versions.length === 0
  return (
    <div className="version-bar">
      {none ? (
        <p>{strings.versionNone}</p>
      ) : (
        <>
          <label htmlFor="spy-version">{strings.versionLabel}</label>
          <select
            id="spy-version"
            value={versionId ?? ''}
            onChange={(event) => onChange(event.target.value)}
          >
            {versions.versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.version}
              </option>
            ))}
          </select>
          {!adding && (
            <button type="button" className="link" onClick={() => setAdding(true)}>
              {strings.versionNew}
            </button>
          )}
        </>
      )}
      {(none || adding) && (
        <form className="version-new" onSubmit={add}>
          <label htmlFor="spy-new-version" className={none ? 'visually-hidden' : undefined}>
            {strings.versionNewLabel}
          </label>
          <input
            id="spy-new-version"
            value={newVersion}
            placeholder={strings.versionPlaceholder}
            onChange={(event) => setNewVersion(event.target.value)}
            autoFocus={adding}
          />
          <button type="submit">{strings.versionAdd}</button>
          {adding && (
            <button type="button" className="link" onClick={() => setAdding(false)}>
              {strings.repoCancel}
            </button>
          )}
        </form>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
