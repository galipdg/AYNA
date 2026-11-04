import { useState, type DragEvent, type KeyboardEvent } from 'react'
import type { RepoObjectSummary } from '../../shared/api.ts'
import {
  CHECK_PROPERTIES,
  KEYWORDS,
  OPERATORS,
  PROBLEM_FIELD,
  isTextProperty,
  move,
  newDraft,
  takesValue,
  type CheckProperty,
  type DraftStep,
  type Keyword,
  type Operator,
  type StepField,
  type StepProblem,
} from '../../shared/steps.ts'
import { serverText, strings } from './strings.ts'

/** The saved elements by screen (the part of the name before the dot), in name order. */
function byScreen(objects: RepoObjectSummary[]): [string, RepoObjectSummary[]][] {
  const groups = new Map<string, RepoObjectSummary[]>()
  for (const object of objects) {
    const screen = object.name.slice(0, object.name.indexOf('.'))
    groups.set(screen, [...(groups.get(screen) ?? []), object])
  }
  return [...groups]
}

export function problemText(problem: StepProblem): string {
  return problem.message ? serverText(problem.message) : strings.stepsProblems[problem.code]
}

/**
 * The codeless step table (#38, wireframe §6): one row per step with its action, element,
 * value and longest wait; rows move by dragging the handle or with Alt+↑ / Alt+↓. A step with
 * problems has its cells marked and one line per reason under it (FR-13).
 */
export default function StepTable({
  drafts,
  problems,
  objects,
  onChange,
}: {
  drafts: DraftStep[]
  problems: StepProblem[]
  /** Null while the saved elements are loading or could not be loaded. */
  objects: RepoObjectSummary[] | null
  onChange: (drafts: DraftStep[]) => void
}) {
  const [dragFrom, setDragFrom] = useState<number>()
  const [dropAt, setDropAt] = useState<number>()
  const [focusKey, setFocusKey] = useState<string>()
  const groups = byScreen(objects ?? [])
  const known = new Set((objects ?? []).map((object) => object.name))

  function update(index: number, change: Partial<DraftStep>) {
    onChange(drafts.map((draft, i) => (i === index ? { ...draft, ...change } : draft)))
  }

  function add() {
    const draft = newDraft()
    setFocusKey(draft.key)
    onChange([...drafts, draft])
  }

  /** Alt+↑ / Alt+↓ move the step; the control that had focus keeps it. */
  function keyDown(event: KeyboardEvent, index: number) {
    if (!event.altKey || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return
    event.preventDefault()
    const to = index + (event.key === 'ArrowUp' ? -1 : 1)
    if (to < 0 || to >= drafts.length) return
    const focused = event.target as HTMLElement
    onChange(move(drafts, index, to))
    requestAnimationFrame(() => {
      if (focused.isConnected && document.activeElement !== focused) focused.focus()
    })
  }

  function dragOver(event: DragEvent, index: number) {
    if (dragFrom === undefined) return
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
    setDropAt(index)
  }

  function drop(event: DragEvent, index: number) {
    if (dragFrom === undefined) return
    event.preventDefault()
    onChange(move(drafts, dragFrom, index))
    dragEnd()
  }

  function dragEnd() {
    setDragFrom(undefined)
    setDropAt(undefined)
  }

  if (drafts.length === 0) {
    return (
      <div className="empty">
        <p className="empty-title">{strings.stepsEmpty}</p>
        <button type="button" className="btn-main" onClick={add}>
          + {strings.stepsAdd}
        </button>
      </div>
    )
  }

  return (
    <>
      <table className="steps" aria-label={strings.stepsLabel}>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">{strings.stepsDrag}</span>
            </th>
            <th scope="col">{strings.stepsHeaderStep}</th>
            <th scope="col">{strings.stepsHeaderAction}</th>
            <th scope="col">{strings.stepsHeaderElement}</th>
            <th scope="col">{strings.stepsHeaderValue}</th>
            <th scope="col">{strings.stepsHeaderTimeout}</th>
            <th scope="col">
              <span className="visually-hidden">{strings.stepsRemove}</span>
            </th>
          </tr>
        </thead>
        {drafts.map((draft, index) => {
          const mine = problems.filter((problem) => problem.index === index)
          const wrong = (field: StepField) =>
            mine.some((problem) => PROBLEM_FIELD[problem.code] === field) || undefined
          const label = (column: string) => strings.stepsCell(column, index + 1)
          const problemId = `step-problems-${draft.key}`
          const describedBy = mine.length > 0 ? problemId : undefined
          const dropClass =
            dropAt === index && dragFrom !== undefined && dragFrom !== index
              ? dragFrom > index
                ? 'drop-before'
                : 'drop-after'
              : undefined
          // A <tbody> per step keeps its problem line with it when rows move.
          return (
            <tbody
              key={draft.key}
              className={[
                'step',
                mine.length > 0 && 'invalid',
                dragFrom === index && 'dragging',
                dropClass,
              ]
                .filter(Boolean)
                .join(' ')}
              onDragOver={(event) => dragOver(event, index)}
              onDrop={(event) => drop(event, index)}
              onKeyDown={(event) => keyDown(event, index)}
            >
              <tr>
                <td className="step-handle">
                  <span
                    draggable
                    title={strings.stepsDrag}
                    aria-hidden="true"
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = 'move'
                      event.dataTransfer.setData('text/plain', String(index + 1))
                      setDragFrom(index)
                    }}
                    onDragEnd={dragEnd}
                  >
                    ⠿
                  </span>
                </td>
                <td className="step-number">
                  {mine.length > 0 && <span aria-hidden="true">✕ </span>}
                  {index + 1}
                </td>
                <td>
                  <select
                    aria-label={label(strings.stepsHeaderAction)}
                    aria-invalid={wrong('keyword')}
                    aria-describedby={describedBy}
                    value={draft.keyword}
                    onChange={(event) => update(index, { keyword: event.target.value as Keyword })}
                  >
                    {!draft.keyword && (
                      <option value="" disabled>
                        {strings.stepsChooseAction}
                      </option>
                    )}
                    {KEYWORDS.map((keyword) => (
                      <option key={keyword} value={keyword}>
                        {strings.stepsKeywords[keyword]}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select
                    aria-label={label(strings.stepsHeaderElement)}
                    aria-invalid={wrong('target')}
                    aria-describedby={describedBy}
                    value={draft.target}
                    autoFocus={draft.key === focusKey}
                    onChange={(event) => update(index, { target: event.target.value })}
                  >
                    <option value="" disabled>
                      {strings.stepsChooseElement}
                    </option>
                    {draft.target && !known.has(draft.target) && (
                      <option value={draft.target}>
                        {strings.stepsMissingElement(draft.target)}
                      </option>
                    )}
                    {groups.map(([screen, items]) => (
                      <optgroup key={screen} label={screen}>
                        {items.map((object) => (
                          <option key={object.id} value={object.name}>
                            {object.name}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </td>
                <td>
                  <ValueCell
                    draft={draft}
                    label={label(strings.stepsHeaderValue)}
                    invalid={wrong('value')}
                    describedBy={describedBy}
                    onChange={(change) => update(index, change)}
                  />
                </td>
                <td>
                  <div className="step-timeout">
                    <input
                      aria-label={label(strings.stepsHeaderTimeout)}
                      aria-invalid={wrong('timeout')}
                      aria-describedby={describedBy}
                      inputMode="decimal"
                      placeholder={strings.stepsTimeoutPlaceholder}
                      value={draft.timeout}
                      onChange={(event) => update(index, { timeout: event.target.value })}
                    />
                    <span className="hint">{strings.stepsSeconds}</span>
                  </div>
                </td>
                <td className="step-actions">
                  <button
                    type="button"
                    className="btn-quiet"
                    title={strings.stepsMoveUp}
                    aria-label={label(strings.stepsMoveUp)}
                    disabled={index === 0}
                    onClick={() => onChange(move(drafts, index, index - 1))}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="btn-quiet"
                    title={strings.stepsMoveDown}
                    aria-label={label(strings.stepsMoveDown)}
                    disabled={index === drafts.length - 1}
                    onClick={() => onChange(move(drafts, index, index + 1))}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="btn-quiet"
                    title={strings.stepsRemove}
                    aria-label={label(strings.stepsRemove)}
                    onClick={() => onChange(drafts.filter((_, i) => i !== index))}
                  >
                    ✕
                  </button>
                </td>
              </tr>
              {mine.length > 0 && (
                <tr className="step-problems">
                  <td />
                  <td colSpan={6}>
                    <ul id={problemId}>
                      {mine.map((problem) => (
                        <li key={`${problem.code} ${problem.message ?? ''}`}>
                          {problemText(problem)}
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              )}
            </tbody>
          )
        })}
      </table>
      <button type="button" className="steps-add" onClick={add}>
        + {strings.stepsAdd}
      </button>
    </>
  )
}

/** What the action needs: text to type, an item to choose, a check, or nothing. */
function ValueCell({
  draft,
  label,
  invalid,
  describedBy,
  onChange,
}: {
  draft: DraftStep
  label: string
  invalid?: boolean
  describedBy?: string
  onChange: (change: Partial<DraftStep>) => void
}) {
  const common = { 'aria-invalid': invalid, 'aria-describedby': describedBy }
  if (takesValue(draft.keyword)) {
    return (
      <input
        {...common}
        aria-label={label}
        placeholder={
          draft.keyword === 'Type' ? strings.stepsValuePlaceholder : strings.stepsItemPlaceholder
        }
        value={draft.value}
        onChange={(event) => onChange({ value: event.target.value })}
      />
    )
  }
  if (draft.keyword !== 'Verify') {
    return <span className="visually-hidden">{strings.stepsNoValue}</span>
  }
  const text = isTextProperty(draft.property)
  return (
    <div className="step-check">
      <select
        {...common}
        aria-label={label}
        value={draft.property}
        onChange={(event) => onChange({ property: event.target.value as CheckProperty })}
      >
        {CHECK_PROPERTIES.map((property) => (
          <option key={property} value={property}>
            {strings.stepsProperties[property]}
          </option>
        ))}
      </select>
      {text ? (
        <>
          <select
            {...common}
            aria-label={label}
            value={draft.operator}
            onChange={(event) => onChange({ operator: event.target.value as Operator })}
          >
            {OPERATORS.map((operator) => (
              <option key={operator} value={operator}>
                {strings.stepsOperators[operator]}
              </option>
            ))}
          </select>
          <input
            {...common}
            aria-label={label}
            placeholder={strings.stepsExpectedPlaceholder}
            value={draft.expectedText}
            onChange={(event) => onChange({ expectedText: event.target.value })}
          />
        </>
      ) : (
        <>
          <span className="hint">{strings.stepsOperators.equals}</span>
          <select
            {...common}
            aria-label={label}
            value={String(draft.expectedFlag)}
            onChange={(event) => onChange({ expectedFlag: event.target.value === 'true' })}
          >
            <option value="true">{strings.stepsYes}</option>
            <option value="false">{strings.stepsNo}</option>
          </select>
        </>
      )}
    </div>
  )
}
