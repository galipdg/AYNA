import { useState, type FormEvent } from 'react'
import type { AddToRepositoryResult, RepoObject } from '../../shared/api.ts'
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
 * Stores the chosen element of a capture in the application's object repository (FR-06).
 * Most of the time only a name is needed: the properties AYNA finds the element by are
 * suggested from the capture and shown as a short summary; "Advanced settings" lets the
 * user edit them. The version comes from the Spy's version bar.
 */
export default function AddToRepository({
  appId,
  snapshot,
  node,
  versionId,
  onSaved,
  onCancel,
}: {
  appId: string
  snapshot: Snapshot
  node: TreeNode
  versionId?: string
  onSaved: (object: RepoObject) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [rows, setRows] = useState<Row[]>(() => initialRows(node, snapshot))
  const [advanced, setAdvanced] = useState(false)
  const [saving, setSaving] = useState(false)
  const [problems, setProblems] = useState<string[]>([])

  function change(field: IdentifyingField, update: Partial<Row>) {
    setRows((current) => current.map((row) => (row.field === field ? { ...row, ...update } : row)))
  }

  const primary = propertySet(rows, 'primary')
  const matches = typeof primary === 'string' ? undefined : matchCount(primary, snapshot.elements)
  const findBy = rows.filter((row) => row.use === 'primary')
  const backup = rows.filter((row) => row.use === 'fallback')

  async function save(event: FormEvent) {
    event.preventDefault()
    const fallback = propertySet(rows, 'fallback')
    const nameProblem = logicalNameProblem(name)
    const propertyProblems = [
      typeof primary === 'string' && primary,
      typeof primary !== 'string' && Object.keys(primary).length === 0 && strings.repoNoPrimary,
      typeof fallback === 'string' && fallback,
    ].filter((problem): problem is string => !!problem)
    const found = nameProblem
      ? [strings.repoNameProblems[nameProblem], ...propertyProblems]
      : propertyProblems
    setProblems(found)
    // Property problems are fixed in the advanced settings, so open them.
    if (propertyProblems.length) setAdvanced(true)
    if (found.length || !versionId || typeof primary === 'string' || typeof fallback === 'string') {
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

        <h4>{strings.repoFoundBy}</h4>
        <div className="repo-summary">
          {findBy.length === 0 ? (
            <p className="error">{strings.repoNoPrimary}</p>
          ) : (
            <dl>
              {findBy.map((row) => (
                <div key={row.field}>
                  <dt>{strings.spyProperties[row.field]}</dt>
                  <dd>{row.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {matches !== undefined && findBy.length > 0 && (
            <p className={matches === 1 ? 'ok' : 'error'} role="status">
              {strings.repoMatches(matches)}
            </p>
          )}
          {backup.length > 0 && (
            <p className="spy-pending">
              {strings.repoBackup(backup.map((row) => strings.spyProperties[row.field]))}
            </p>
          )}
        </div>

        <details
          className="repo-advanced"
          open={advanced}
          onToggle={(event) => setAdvanced(event.currentTarget.open)}
        >
          <summary>{strings.repoAdvanced}</summary>
          <p className="spy-pending">{strings.repoAdvancedHint}</p>
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
        </details>

        {!versionId && <p className="error">{strings.repoNoVersion}</p>}
        {problems.length > 0 && (
          <ul className="error" role="alert">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
        <div className="actions">
          <button type="submit" disabled={saving || !versionId}>
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
