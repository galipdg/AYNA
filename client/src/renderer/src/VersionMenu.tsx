import { useEffect, useState, type FormEvent } from 'react'
import type { AppVersion } from '../../shared/api.ts'
import Icon from './Icons.tsx'
import Menu from './Menu.tsx'
import { strings } from './strings.ts'

type Versions =
  | { state: 'loading' }
  | { state: 'loaded'; versions: AppVersion[] }
  | { state: 'failed'; message: string }

/**
 * The application version every screen works with: chosen once here, in the top bar, never
 * in a form (#183). Without versions it asks for the one being tested. Mount it with a `key`
 * per application.
 */
export default function VersionMenu({
  appId,
  version,
  onChange,
  onSessionEnded,
}: {
  appId: string
  version?: AppVersion
  onChange: (version: AppVersion) => void
  onSessionEnded: () => void
}) {
  const [versions, setVersions] = useState<Versions>({ state: 'loading' })
  const [newVersion, setNewVersion] = useState('')
  const [error, setError] = useState<string>()

  const loading = versions.state === 'loading'
  const versionId = version?.id
  useEffect(() => {
    if (!loading) return
    let cancelled = false
    window.ayna.listVersions(appId).then(
      (result) => {
        if (cancelled) return
        if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
        if (!result.ok) {
          return setVersions({ state: 'failed', message: strings.versionErrors[result.reason] })
        }
        setVersions({ state: 'loaded', versions: result.versions })
        // Keep the choice if it still exists; otherwise the newest-listed version.
        const kept = result.versions.find((candidate) => candidate.id === versionId)
        const newest = result.versions.at(-1)
        if (!kept && newest) onChange(newest)
      },
      () => !cancelled && setVersions({ state: 'failed', message: strings.bridgeError }),
    )
    return () => {
      cancelled = true
    }
  }, [loading, appId, versionId, onChange, onSessionEnded])

  async function add(event: FormEvent, close: () => void) {
    event.preventDefault()
    setError(undefined)
    const text = newVersion.trim()
    if (!text) return setError(strings.versionErrors.invalid)
    try {
      const result = await window.ayna.createVersion(appId, text)
      if (!result.ok && result.reason === 'unauthorized') return onSessionEnded()
      if (!result.ok) return setError(result.detail ?? strings.versionErrors[result.reason])
      setNewVersion('')
      onChange(result.version)
      setVersions({ state: 'loading' })
      close()
    } catch {
      setError(strings.bridgeError)
    }
  }

  const none = versions.state === 'loaded' && versions.versions.length === 0
  const label =
    versions.state === 'loading' ? (
      strings.loading
    ) : versions.state === 'failed' ? (
      <span className="tone-danger">{strings.topVersionTitle}</span>
    ) : none ? (
      `+ ${strings.topVersionNone}`
    ) : (
      version && strings.topVersion(version.version)
    )

  return (
    <Menu
      title={strings.topVersionTitle}
      className={none || versions.state === 'failed' ? 'attention' : undefined}
      label={
        <>
          {label}
          <Icon name="chevron" />
        </>
      }
    >
      {(close) => (
        <div className="menu-body">
          <p className="menu-title">{strings.topVersionTitle}</p>
          <p className="hint">{none ? strings.versionNone : strings.topVersionHint}</p>
          {versions.state === 'failed' && (
            <div className="message message-danger" role="alert">
              <Icon name="warning" />
              <span>{versions.message}</span>
              <button
                type="button"
                className="btn-quiet"
                onClick={() => setVersions({ state: 'loading' })}
              >
                {strings.versionRetry}
              </button>
            </div>
          )}
          {versions.state === 'loaded' && versions.versions.length > 0 && (
            <ul className="choice-list">
              {/* Newest first. */}
              {[...versions.versions].reverse().map((candidate) => (
                <li key={candidate.id}>
                  <button
                    type="button"
                    className={candidate.id === versionId ? 'selected' : undefined}
                    aria-pressed={candidate.id === versionId}
                    onClick={() => {
                      onChange(candidate)
                      close()
                    }}
                  >
                    {strings.topVersion(candidate.version)}
                    {candidate.id === versionId && <Icon name="check" />}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {versions.state === 'loaded' && (
            <form className="inline-form" onSubmit={(event) => add(event, close)}>
              <label htmlFor="new-version">{strings.versionNewLabel}</label>
              <div className="field-row">
                <input
                  id="new-version"
                  value={newVersion}
                  placeholder={strings.versionPlaceholder}
                  onChange={(event) => setNewVersion(event.target.value)}
                  aria-invalid={error ? true : undefined}
                  autoFocus={none}
                />
                <button type="submit" className={none ? 'btn-main' : undefined}>
                  {strings.versionAdd}
                </button>
              </div>
              {error && (
                <p className="field-error" role="alert">
                  {error}
                </p>
              )}
            </form>
          )}
        </div>
      )}
    </Menu>
  )
}
