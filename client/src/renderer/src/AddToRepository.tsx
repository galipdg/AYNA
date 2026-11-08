import { useEffect, useState, type FormEvent } from 'react'
import type {
  AddToRepositoryResult,
  AppVersion,
  Application,
  RepoObject,
  RepoObjectSummary,
} from '../../shared/api.ts'
import {
  logicalNameProblem,
  matchCount,
  objectsMatching,
  suggestUses,
  type IdentifyingField,
} from '../../shared/repository.ts'
import type { Snapshot, TreeNode } from '../../shared/snapshot.ts'
import {
  FoundBy,
  PropertyTable,
  elementRows,
  propertySet,
  rowProblems,
  type Row,
} from './PropertySetEditor.tsx'
import { serverText, strings } from './strings.ts'

/** The element's identifying properties, best first, with the suggested use of each. */
function initialRows(node: TreeNode, snapshot: Snapshot): Row[] {
  const uses = suggestUses(node.element, snapshot.elements)
  return elementRows(node.element, (field) => uses[field]!)
}

function failureText(result: Extract<AddToRepositoryResult, { ok: false }>): string[] {
  // Our text says what to do next; the server's says which object holds the name.
  const main =
    result.reason === 'snapshot-conflict'
      ? strings.repoErrors[result.reason]
      : result.detail
        ? serverText(result.detail)
        : strings.repoErrors[result.reason]
  return [main, ...(result.fields ?? []).map((field) => serverText(field.message))]
}

/**
 * Stores the chosen element of a capture in the application's object repository (FR-06).
 * Most of the time only a name is needed: the properties AYNA finds the element by are
 * suggested from the capture and shown as a short summary; "Advanced settings" lets the
 * user edit them. The version comes from the top bar.
 */
export default function AddToRepository({
  app,
  snapshot,
  node,
  version,
  onSaved,
  onCancel,
}: {
  app: Application
  snapshot: Snapshot
  node: TreeNode
  version?: AppVersion
  onSaved: (object: RepoObject) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [rows, setRows] = useState<Row[]>(() => initialRows(node, snapshot))
  const [advanced, setAdvanced] = useState(false)
  const [saving, setSaving] = useState(false)
  const [problems, setProblems] = useState<string[]>([])
  const [savedAs, setSavedAs] = useState<RepoObjectSummary[]>([])

  // Is this element saved already? Only a hint: saving it again under another name is allowed.
  useEffect(() => {
    let cancelled = false
    window.ayna
      .listRepoObjects(app.id)
      .then((result) => {
        if (!cancelled && result.ok) setSavedAs(objectsMatching(result.objects, node.element))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [app.id, node])

  function change(field: IdentifyingField, update: Partial<Row>) {
    setRows((current) => current.map((row) => (row.field === field ? { ...row, ...update } : row)))
  }

  const primary = propertySet(rows, 'primary')
  const matches = typeof primary === 'string' ? undefined : matchCount(primary, snapshot.elements)

  async function save(event: FormEvent) {
    event.preventDefault()
    const fallback = propertySet(rows, 'fallback')
    const nameProblem = logicalNameProblem(name)
    const propertyProblems = rowProblems(rows)
    const found = nameProblem
      ? [strings.repoNameProblems[nameProblem], ...propertyProblems]
      : propertyProblems
    setProblems(found)
    // Property problems are fixed in the advanced settings, so open them.
    if (propertyProblems.length) setAdvanced(true)
    const versionId = version?.id
    if (found.length || !versionId || typeof primary === 'string' || typeof fallback === 'string') {
      return
    }
    setSaving(true)
    try {
      const result = await window.ayna.addToRepository({
        appId: app.id,
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
      <header className="panel-header">
        <div>
          <button type="button" className="btn-quiet" onClick={onCancel} disabled={saving}>
            ← {strings.spyBack}
          </button>
          <h2>{strings.repoTitle}</h2>
        </div>
      </header>
      <form className="repo-form" onSubmit={save}>
        <div className="panel-scroll form">
          <label htmlFor="repo-name">{strings.repoNameLabel}</label>
          <input
            id="repo-name"
            value={name}
            placeholder={strings.repoNamePlaceholder}
            onChange={(event) => setName(event.target.value)}
            aria-describedby="repo-name-hint"
            autoFocus
          />
          <p id="repo-name-hint" className="hint">
            {strings.repoNameHint}
          </p>

          {savedAs.length > 0 && (
            <p className="message message-warning" role="status">
              {strings.repoAlreadySaved(savedAs.map((object) => object.name))}
            </p>
          )}

          <h4>{strings.repoFoundBy}</h4>
          <FoundBy rows={rows} matches={matches} />

          <details
            className="advanced"
            open={advanced}
            onToggle={(event) => setAdvanced(event.currentTarget.open)}
          >
            <summary>{strings.repoAdvanced}</summary>
            <p className="hint">{strings.repoAdvancedHint}</p>
            <PropertyTable rows={rows} onChange={change} />
          </details>

          {problems.length > 0 && (
            <ul className="message message-danger" role="alert">
              {problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          )}
        </div>
        <footer className="panel-footer">
          <p className={version ? 'hint' : 'field-error'}>
            {version ? strings.repoSavedUnder(app.name, version.version) : strings.repoNoVersion}
          </p>
          <div className="form-actions">
            <button type="button" onClick={onCancel} disabled={saving}>
              {strings.repoCancel}
            </button>
            <button
              type="submit"
              className="btn-main"
              disabled={saving || !version}
              title={version ? undefined : strings.repoNoVersion}
            >
              {saving ? strings.repoSaving : strings.repoSave}
            </button>
          </div>
        </footer>
      </form>
    </section>
  )
}
