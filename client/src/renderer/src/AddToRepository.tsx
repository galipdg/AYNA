import { useEffect, useState, type FormEvent } from 'react'
import type { AddToRepositoryResult, AppVersion, RepoObject } from '../../shared/api.ts'
import {
  IDENTIFYING_FIELDS,
  logicalNameProblem,
  matchCount,
  suggestUses,
  type IdentifyingField,
  type PropertySet,
  type PropertyUse,
} from '../../shared/repository.ts'
import type { Snapshot, TreeNode } from '../../shared/snapshot.ts'
import { strings } from './strings.ts'

type Versions =
  | { state: 'loading' }
  | { state: 'loaded'; versions: AppVersion[] }
  | { state: 'failed'; message: string }

interface Row {
  field: IdentifyingField
  value: string
  use: PropertyUse
}

/** The element's identifying properties, best first, with the suggested use of each. */
function initialRows(node: TreeNode, snapshot: Snapshot): Row[] {
  const uses = suggestUses(node.element, snapshot.elements)
  return IDENTIFYING_FIELDS.flatMap((field) => {
    const value = node.element[field]
    return value === undefined ? [] : [{ field, value: String(value), use: uses[field]! }]
  })
}

/** The rows of one use as a property set, or the first problem with their values. */
function propertySet(rows: Row[], use: PropertyUse): PropertySet | string {
  const set: Record<string, string | number> = {}
  for (const row of rows.filter((candidate) => candidate.use === use)) {
    const label = strings.spyProperties[row.field]
    if (row.field === 'siblingIndex') {
      if (!/^\d+$/.test(row.value.trim())) return strings.repoNotInteger(label)
      set[row.field] = Number(row.value.trim())
    } else {
      // Kept as typed: a value with surrounding spaces is still a real UIA value.
      if (!row.value) return strings.repoEmptyValue(label)
      set[row.field] = row.value
    }
  }
  return set as PropertySet
}

function failureText(result: Extract<AddToRepositoryResult, { ok: false }>): string[] {
  // Our text says what to do next; the server's says which object holds the name.
  const main =
    result.reason === 'snapshot-conflict'
      ? strings.repoErrors[result.reason]
      : (result.detail ?? strings.repoErrors[result.reason])
  return [main, ...(result.fields ?? []).map((field) => field.message)]
}

/**
 * Stores the chosen element of a capture in the application's object repository: a logical
 * name, the version the capture belongs to, and the primary and fallback properties,
 * suggested from the element and editable before saving (FR-06).
 */
export default function AddToRepository({
  appId,
  snapshot,
  node,
  versionId,
  onVersionChosen,
  onSaved,
  onCancel,
}: {
  appId: string
  snapshot: Snapshot
  node: TreeNode
  /** The version chosen last time, kept by the Spy while it is open. */
  versionId?: string
  onVersionChosen: (versionId: string) => void
  onSaved: (object: RepoObject) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [rows, setRows] = useState<Row[]>(() => initialRows(node, snapshot))
  const [versions, setVersions] = useState<Versions>({ state: 'loading' })
  const [newVersion, setNewVersion] = useState('')
  const [versionError, setVersionError] = useState<string>()
  const [saving, setSaving] = useState(false)
  const [problems, setProblems] = useState<string[]>([])

  const loadingVersions = versions.state === 'loading'
  useEffect(() => {
    if (!loadingVersions) return
    let cancelled = false
    window.ayna.listVersions(appId).then(
      (result) => {
        if (cancelled) return
        if (!result.ok) {
          return setVersions({ state: 'failed', message: strings.versionErrors[result.reason] })
        }
        setVersions({ state: 'loaded', versions: result.versions })
        // Keep the last choice if it still exists; otherwise the newest-listed version.
        const kept = result.versions.find((version) => version.id === versionId)
        const fallback = result.versions.at(-1)
        if (!kept && fallback) onVersionChosen(fallback.id)
      },
      () => !cancelled && setVersions({ state: 'failed', message: strings.bridgeError }),
    )
    return () => {
      cancelled = true
    }
  }, [loadingVersions, appId, versionId, onVersionChosen])

  async function addVersion() {
    setVersionError(undefined)
    const version = newVersion.trim()
    if (!version) return setVersionError(strings.versionErrors.invalid)
    const result = await window.ayna.createVersion(appId, version)
    if (!result.ok) return setVersionError(result.detail ?? strings.versionErrors[result.reason])
    setNewVersion('')
    onVersionChosen(result.version.id)
    setVersions({ state: 'loading' })
  }

  function change(field: IdentifyingField, update: Partial<Row>) {
    setRows((current) => current.map((row) => (row.field === field ? { ...row, ...update } : row)))
  }

  const primary = propertySet(rows, 'primary')
  const matches = typeof primary === 'string' ? undefined : matchCount(primary, snapshot.elements)

  async function save(event: FormEvent) {
    event.preventDefault()
    const fallback = propertySet(rows, 'fallback')
    const nameProblem = logicalNameProblem(name)
    const found = [
      nameProblem && strings.repoNameProblems[nameProblem],
      typeof primary === 'string' && primary,
      typeof primary !== 'string' && Object.keys(primary).length === 0 && strings.repoNoPrimary,
      typeof fallback === 'string' && fallback,
    ].filter((problem): problem is string => !!problem)
    if (!versionId) found.push(strings.repoNoVersions)
    setProblems(found)
    if (found.length || typeof primary === 'string' || typeof fallback === 'string' || !versionId) {
      return
    }
    setSaving(true)
    try {
      const result = await window.ayna.addToRepository({
        appId,
        versionId,
        snapshot,
        snapshotElementId: node.id,
        name: name.trim(),
        primary,
        fallback,
      })
      if (result.ok) return onSaved(result.object)
      setProblems(failureText(result))
    } catch {
      setProblems([strings.bridgeError])
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="spy-repo" aria-label={strings.repoTitle}>
      <h3>{strings.repoTitle}</h3>
      <form className="app-form" onSubmit={save}>
        <label htmlFor="repo-name">{strings.repoNameLabel}</label>
        <input
          id="repo-name"
          value={name}
          placeholder={strings.repoNamePlaceholder}
          onChange={(event) => setName(event.target.value)}
          aria-describedby="repo-name-hint"
          autoFocus
        />
        <p id="repo-name-hint" className="spy-pending">
          {strings.repoNameHint}
        </p>

        <label htmlFor="repo-version">{strings.repoVersionLabel}</label>
        {versions.state === 'loading' && <p>{strings.loading}</p>}
        {versions.state === 'failed' && (
          <p className="error" role="alert">
            {versions.message}
          </p>
        )}
        {versions.state === 'loaded' && versions.versions.length === 0 && (
          <p className="spy-pending">{strings.repoNoVersions}</p>
        )}
        {versions.state === 'loaded' && versions.versions.length > 0 && (
          <select
            id="repo-version"
            value={versionId ?? ''}
            onChange={(event) => onVersionChosen(event.target.value)}
            aria-describedby="repo-version-hint"
          >
            {versions.versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.version}
              </option>
            ))}
          </select>
        )}
        <p id="repo-version-hint" className="spy-pending">
          {strings.repoVersionHint}
        </p>
        <div className="actions">
          <label htmlFor="repo-new-version">{strings.repoNewVersionLabel}</label>
          <input
            id="repo-new-version"
            value={newVersion}
            placeholder={strings.repoNewVersionPlaceholder}
            onChange={(event) => setNewVersion(event.target.value)}
          />
          <button type="button" onClick={addVersion}>
            {strings.repoAddVersion}
          </button>
        </div>
        {versionError && (
          <p className="error" role="alert">
            {versionError}
          </p>
        )}

        <h4>{strings.repoPropertiesTitle}</h4>
        <p className="spy-pending">{strings.repoPropertiesHint}</p>
        <table className="repo-properties">
          <thead>
            <tr>
              <th scope="col">{strings.repoPropertyHeader}</th>
              <th scope="col">{strings.repoValueHeader}</th>
              <th scope="col">{strings.repoUseHeader}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const label = strings.spyProperties[row.field]
              return (
                <tr key={row.field}>
                  <th scope="row" title={row.field}>
                    {label}
                  </th>
                  <td>
                    <input
                      aria-label={`${label}: ${strings.repoValueHeader}`}
                      value={row.value}
                      inputMode={row.field === 'siblingIndex' ? 'numeric' : undefined}
                      onChange={(event) => change(row.field, { value: event.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`${label}: ${strings.repoUseHeader}`}
                      value={row.use}
                      onChange={(event) =>
                        change(row.field, { use: event.target.value as PropertyUse })
                      }
                    >
                      {(['primary', 'fallback', 'unused'] as const).map((use) => (
                        <option key={use} value={use}>
                          {strings.repoUses[use]}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {matches !== undefined && Object.keys(primary).length > 0 && (
          <p className={matches === 1 ? 'spy-pending' : 'error'} role="status">
            {strings.repoMatches(matches)}
          </p>
        )}

        {problems.length > 0 && (
          <ul className="error" role="alert">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
        <div className="actions">
          <button type="submit" disabled={saving}>
            {saving ? strings.repoSaving : strings.repoSave}
          </button>
          <button type="button" onClick={onCancel} disabled={saving}>
            {strings.repoCancel}
          </button>
        </div>
      </form>
    </section>
  )
}
