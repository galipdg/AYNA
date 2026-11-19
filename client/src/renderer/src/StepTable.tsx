import {
  useId,
  useRef,
  useState,
  type CSSProperties,
  type DragEvent,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from 'react'
import type { RepoObjectSummary } from '../../shared/api.ts'
import type { RowState } from '../../shared/liveRun.ts'
import {
  CHECK_PROPERTIES,
  GRID_CONTROL_TYPES,
  KEYWORDS,
  OPERATORS,
  PROBLEM_FIELD,
  ROW_CONTROL_TYPES,
  checkKind,
  fitsTarget,
  move,
  newDraft,
  readsRow,
  takesValue,
  targetTypes,
  type CheckProperty,
  type DraftStep,
  type Keyword,
  type Operator,
  type StepField,
  type StepProblem,
} from '../../shared/steps.ts'
import Resizer from './Resizer.tsx'
import { formatDuration, serverText, strings } from './strings.ts'

/** The saved elements by screen (the part of the name before the dot), in name order. */
function byScreen(objects: RepoObjectSummary[]): [string, RepoObjectSummary[]][] {
  const groups = new Map<string, RepoObjectSummary[]>()
  for (const object of objects) {
    const screen = object.name.slice(0, object.name.indexOf('.'))
    groups.set(screen, [...(groups.get(screen) ?? []), object])
  }
  return [...groups]
}

/** The fields filled in by typing; the others change in one go. */
const TYPED_FIELDS = [
  'value',
  'expectedText',
  'expectedCount',
  'rowIndex',
  'rowValue',
  'rowColumn',
  'column',
  'timeout',
] as const

/** The columns a user can widen or narrow: default, smallest and largest width in px. */
const COLUMNS = {
  action: { initial: 124, min: 100, max: 280 },
  element: { initial: 240, min: 140, max: 520 },
} as const
type Column = keyof typeof COLUMNS

/** The last widths chosen, kept while the app runs so another test opens with them. */
let chosenWidths: Record<Column, number> = {
  action: COLUMNS.action.initial,
  element: COLUMNS.element.initial,
}

/**
 * The handle, number, wait and row-button columns, as in `styles.css`, plus the least the value
 * column can work with. The table fits the default window; widening a column beyond that
 * makes it scroll instead of squeezing the values.
 */
const OTHER_COLUMNS_WIDTH = 20 + 44 + 120 + 96 + 96

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
  readOnly = false,
  results = null,
}: {
  drafts: DraftStep[]
  problems: StepProblem[]
  /** Null while the saved elements are loading or could not be loaded. */
  objects: RepoObjectSummary[] | null
  /** `typedField` names a text field, so keystrokes in it undo as one change. */
  onChange: (drafts: DraftStep[], typedField?: string) => void
  /** While a run plays: nothing can be changed or moved (wireframe 8). */
  readOnly?: boolean
  /** Each step's run result, in step order; null hides the Result column. */
  results?: RowState[] | null
}) {
  const [dragFrom, setDragFrom] = useState<number>()
  const [dropAt, setDropAt] = useState<number>()
  const [focusKey, setFocusKey] = useState<string>()
  const [widths, setWidths] = useState(chosenWidths)
  const known = new Set((objects ?? []).map((object) => object.name))
  const columnsOf = new Map((objects ?? []).map((object) => [object.name, object.columns]))
  // The elements each kind of action can use: any, grids and lists, grids (`targetTypes`).
  const offered = new Map(
    [undefined, ROW_CONTROL_TYPES, GRID_CONTROL_TYPES].map((types) => [
      types,
      byScreen((objects ?? []).filter((object) => fitsTarget(types, object.controlType))),
    ]),
  )

  function resize(column: Column, width: number) {
    const { min, max } = COLUMNS[column]
    chosenWidths = { ...widths, [column]: Math.round(Math.min(max, Math.max(min, width))) }
    setWidths(chosenWidths)
  }

  function update(index: number, change: Partial<DraftStep>) {
    const typed = TYPED_FIELDS.find((field) => field in change)
    onChange(
      drafts.map((draft, i) => (i === index ? { ...draft, ...change } : draft)),
      typed && `${drafts[index].key}:${typed}`,
    )
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
    <fieldset className="steps-fieldset" disabled={readOnly}>
      <table
        className="steps"
        aria-label={strings.stepsLabel}
        style={{
          minWidth:
            OTHER_COLUMNS_WIDTH + widths.action + widths.element + (results ? RESULT_WIDTH : 0),
        }}
      >
        <colgroup>
          <col className="col-handle" />
          <col className="col-number" />
          <col style={{ width: widths.action }} />
          <col style={{ width: widths.element }} />
          <col className="col-value" />
          <col className="col-timeout" />
          {results && <col className="col-result" />}
          <col className="col-actions" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">{strings.stepsDrag}</span>
            </th>
            <th scope="col">{strings.stepsHeaderStep}</th>
            <th scope="col" className="resizable">
              {strings.stepsHeaderAction}
              <Resizer
                className="column-resizer"
                label={strings.stepsResize(strings.stepsHeaderAction)}
                width={widths.action}
                {...COLUMNS.action}
                onResize={(width) => resize('action', width)}
              />
            </th>
            <th scope="col" className="resizable">
              {strings.stepsHeaderElement}
              <Resizer
                className="column-resizer"
                label={strings.stepsResize(strings.stepsHeaderElement)}
                width={widths.element}
                {...COLUMNS.element}
                onResize={(width) => resize('element', width)}
              />
            </th>
            <th scope="col">{strings.stepsHeaderValue}</th>
            <th scope="col">{strings.stepsHeaderTimeout}</th>
            {results && <th scope="col">{strings.runHeaderResult}</th>}
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
          const types = targetTypes(draft)
          const groups = offered.get(types) ?? []
          const offeredHere = groups.some(([, items]) =>
            items.some((object) => object.name === draft.target),
          )
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
                    draggable={!readOnly}
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
                      {types === undefined
                        ? strings.stepsChooseElement
                        : types === GRID_CONTROL_TYPES
                          ? strings.stepsChooseGrid
                          : strings.stepsChooseRows}
                    </option>
                    {draft.target && !known.has(draft.target) && (
                      <option value={draft.target}>
                        {strings.stepsMissingElement(draft.target)}
                      </option>
                    )}
                    {/* A saved element that does not fit the action stays chosen; its problem says why. */}
                    {draft.target && known.has(draft.target) && !offeredHere && (
                      <option value={draft.target}>{draft.target}</option>
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
                    columns={columnsOf.get(draft.target) ?? []}
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
                {results && <ResultCell state={results[index] ?? { kind: 'pending' }} />}
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
              {results?.[index]?.kind === 'failed' && results[index].outcome?.message && (
                <tr className="step-failure">
                  <td />
                  <td colSpan={results ? 7 : 6}>{serverText(results[index].outcome!.message!)}</td>
                </tr>
              )}
              {mine.length > 0 && (
                <tr className="step-problems">
                  <td />
                  <td colSpan={results ? 7 : 6}>
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
    </fieldset>
  )
}

const RESULT_WIDTH = 150

/** A step's run result (wireframe 8): ✓ time, ● waiting, ✕ category, – skipped, · not yet. */
function ResultCell({ state }: { state: RowState }) {
  const { kind, outcome } = state
  if (kind === 'passed') {
    return (
      <td className="step-result result-passed">
        ✓ {outcome?.durationMs !== null && outcome ? formatDuration(outcome.durationMs) : ''}
      </td>
    )
  }
  if (kind === 'failed') {
    const category = outcome?.category
    return (
      <td className="step-result result-failed">
        ✕ {category ? (strings.runCategories[category] ?? category) : strings.runsStatus.failed}
      </td>
    )
  }
  if (kind === 'playing') {
    return (
      <td className="step-result result-playing">
        ●{' '}
        {strings.runWaiting(formatDuration(state.waitedMs ?? 0), formatDuration(state.timeoutMs ?? 0))}
      </td>
    )
  }
  if (kind === 'skipped') return <td className="step-result result-skipped">– {strings.runSkipped}</td>
  return <td className="step-result result-pending">·</td>
}

/** What the action needs: text to type, an item to choose, a row, a check, or nothing. */
function ValueCell({
  draft,
  columns,
  label,
  invalid,
  describedBy,
  onChange,
}: {
  draft: DraftStep
  /** The target's captured column headers; empty when unknown. */
  columns: string[]
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
  if (draft.keyword === 'SelectRow') {
    return (
      <PopoverCell summary={rowSummary(draft)} label={label} common={common}>
        {(first) => (
          <RowPicker
            first={first}
            common={common}
            draft={draft}
            columns={columns}
            label={label}
            onChange={onChange}
          />
        )}
      </PopoverCell>
    )
  }
  if (draft.keyword !== 'Verify') {
    return <span className="visually-hidden">{strings.stepsNoValue}</span>
  }
  return (
    <PopoverCell summary={checkSummary(draft)} label={label} common={common}>
      {(first) => (
        <CheckFields
          first={first}
          common={common}
          draft={draft}
          columns={columns}
          label={label}
          onChange={onChange}
        />
      )}
    </PopoverCell>
  )
}

/** The row in a few words: "row 2", "row with “Yılmaz” in Surname". */
export function rowSummary(draft: DraftStep): string {
  if (draft.rowBy === 'index') {
    return draft.rowIndex.trim()
      ? strings.stepsRowNumber(draft.rowIndex.trim())
      : strings.stepsRowNone
  }
  return draft.rowValue
    ? strings.stepsRowWithText(draft.rowValue, draft.rowColumn)
    : strings.stepsRowNone
}

/** One line for a check, so a row with a check is as tall as any other. */
export function checkSummary(draft: DraftStep): string {
  const property = strings.stepsProperties[draft.property]
  const kind = checkKind(draft.property)
  if (kind === 'count') {
    return `${property} ${strings.stepsOperators.equals} ${draft.expectedCount.trim() || '?'}`
  }
  const where =
    draft.property === 'cell'
      ? ` (${rowSummary(draft)}, ${draft.column || '?'})`
      : readsRow(draft.property)
        ? ` (${rowSummary(draft)})`
        : ''
  if (kind === 'flag') {
    const expected = draft.expectedFlag ? strings.stepsYes : strings.stepsNo
    return `${property}${where} ${strings.stepsOperators.equals} ${expected}`
  }
  return `${property}${where} ${strings.stepsOperators[draft.operator]} “${draft.expectedText}”`
}

/**
 * A row or a check takes several controls, too many for a table cell. The row shows a summary;
 * a click opens the controls in a popover, which the browser draws above the table's scroll
 * area and closes on Esc or a click outside.
 */
function PopoverCell({
  summary,
  label,
  common,
  children,
}: {
  summary: string
  label: string
  common: Common
  /** The controls; `first` goes on the one that gets focus when the popover opens. */
  children: (first: RefObject<HTMLSelectElement | null>) => ReactNode
}) {
  const id = useId()
  const first = useRef<HTMLSelectElement>(null)
  const anchor = `--check-${id.replace(/\W/g, '')}`
  return (
    <>
      <button
        type="button"
        className="step-check-summary"
        popoverTarget={id}
        title={summary}
        aria-label={`${label}: ${summary}`}
        {...common}
        style={{ anchorName: anchor } as CSSProperties}
      >
        <span>{summary}</span>
      </button>
      <div
        id={id}
        popover="auto"
        className="step-check"
        role="group"
        aria-label={label}
        style={{ positionAnchor: anchor } as CSSProperties}
        onToggle={(event) => {
          if (event.newState === 'open') first.current?.focus()
        }}
      >
        {children(first)}
      </div>
    </>
  )
}

type Common = { 'aria-invalid'?: boolean; 'aria-describedby'?: string }

interface FieldsProps {
  first?: RefObject<HTMLSelectElement | null>
  /** The step's problem marking, on every control. */
  common: Common
  draft: DraftStep
  /** The target's captured column headers; empty when unknown. */
  columns: string[]
  /** The value cell's label; each control adds its own part. */
  label: string
  onChange: (change: Partial<DraftStep>) => void
}

/**
 * The row of SelectRow, `cell` and `rowExists`: its number from the top, or the text of one of
 * its cells, in a given column or any (ADR step-schema-v0-2-rows).
 */
function RowPicker({ first, common, draft, columns, label, onChange }: FieldsProps) {
  return (
    <>
      <div className="step-check-line">
        <select
          ref={first}
          {...common}
          aria-label={`${label}: ${strings.stepsRowBy}`}
          value={draft.rowBy}
          onChange={(event) => onChange({ rowBy: event.target.value as DraftStep['rowBy'] })}
        >
          <option value="index">{strings.stepsRowByIndex}</option>
          <option value="value">{strings.stepsRowByValue}</option>
        </select>
        {draft.rowBy === 'index' ? (
          <input
            {...common}
            aria-label={`${label}: ${strings.stepsRowByIndex}`}
            inputMode="numeric"
            placeholder={strings.stepsRowIndexPlaceholder}
            value={draft.rowIndex}
            onChange={(event) => onChange({ rowIndex: event.target.value })}
          />
        ) : (
          <input
            {...common}
            aria-label={`${label}: ${strings.stepsRowByValue}`}
            maxLength={1000}
            placeholder={strings.stepsRowValuePlaceholder}
            value={draft.rowValue}
            onChange={(event) => onChange({ rowValue: event.target.value })}
          />
        )}
      </div>
      {draft.rowBy === 'value' && (
        <div className="step-check-line">
          <span className="hint">{strings.stepsRowInColumn}</span>
          <ColumnField
            common={common}
            columns={columns}
            label={`${label}: ${strings.stepsRowInColumn}`}
            empty={strings.stepsAnyColumn}
            value={draft.rowColumn}
            onChange={(rowColumn) => onChange({ rowColumn })}
          />
        </div>
      )}
    </>
  )
}

/** The option that switches a column list to free text; no header text starts with a NUL. */
const OTHER_COLUMN = '\u0000other'

/**
 * A column header (#221): a list of the target's captured headers when there are any, else free
 * text. The list may miss columns (scrolled out or virtualised when captured), so "Other…"
 * switches to typing, and a stored column that is not in the list is shown as typed text.
 * `empty` names the empty choice: "any column" for a row's key, "choose a column" for a `cell`
 * check, which needs one (`required`).
 */
function ColumnField({
  common,
  columns,
  label,
  empty,
  placeholder = empty,
  required = false,
  value,
  onChange,
}: {
  common: Common
  columns: string[]
  label: string
  empty: string
  placeholder?: string
  required?: boolean
  value: string
  onChange: (value: string) => void
}) {
  // "Other…" is open for this list of columns only, so choosing another grid closes it (#228).
  const listKey = columns.join('\u0001')
  const [typingFor, setTypingFor] = useState<string | null>(null)
  const typing = typingFor === listKey
  const text = (
    <input
      {...common}
      // Beside the list it needs a name of its own; alone it is the field itself (#228).
      aria-label={columns.length === 0 ? label : `${label}: ${strings.stepsOtherColumn}`}
      maxLength={100}
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  )
  if (columns.length === 0) return text
  const custom = typing || (value !== '' && !columns.includes(value))
  return (
    <>
      <select
        {...common}
        aria-label={label}
        value={custom ? OTHER_COLUMN : value}
        onChange={(event) => {
          const chosen = event.target.value
          setTypingFor(chosen === OTHER_COLUMN ? listKey : null)
          if (chosen !== OTHER_COLUMN) onChange(chosen)
        }}
      >
        <option value="" disabled={required}>
          {empty}
        </option>
        {columns.map((column) => (
          <option key={column} value={column}>
            {column}
          </option>
        ))}
        <option value={OTHER_COLUMN}>{strings.stepsOtherColumn}</option>
      </select>
      {custom && text}
    </>
  )
}

/** The controls of a check: what to read, where (row and column), and what to expect. */
function CheckFields({ first, common, draft, columns, label, onChange }: FieldsProps) {
  const kind = checkKind(draft.property)
  return (
    <>
      <div className="step-check-line">
        <select
          ref={first}
          {...common}
          aria-label={`${label}: ${strings.stepsCheckProperty}`}
          value={draft.property}
          onChange={(event) => onChange({ property: event.target.value as CheckProperty })}
        >
          {CHECK_PROPERTIES.map((property) => (
            <option key={property} value={property}>
              {strings.stepsProperties[property]}
            </option>
          ))}
        </select>
      </div>
      {readsRow(draft.property) && (
        <RowPicker
          common={common}
          draft={draft}
          columns={columns}
          label={label}
          onChange={onChange}
        />
      )}
      {draft.property === 'cell' && (
        <div className="step-check-line">
          <span className="hint">{strings.stepsColumn}</span>
          <ColumnField
            common={common}
            columns={columns}
            label={`${label}: ${strings.stepsColumn}`}
            empty={strings.stepsChooseColumn}
            placeholder={strings.stepsColumnPlaceholder}
            required
            value={draft.column}
            onChange={(column) => onChange({ column })}
          />
        </div>
      )}
      <div className="step-check-line">
        {kind === 'text' ? (
          <>
            <select
              {...common}
              aria-label={`${label}: ${strings.stepsCheckOperator}`}
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
              aria-label={`${label}: ${strings.stepsExpectedPlaceholder}`}
              placeholder={strings.stepsExpectedPlaceholder}
              value={draft.expectedText}
              onChange={(event) => onChange({ expectedText: event.target.value })}
            />
          </>
        ) : kind === 'count' ? (
          <>
            <span className="hint">{strings.stepsOperators.equals}</span>
            <input
              {...common}
              aria-label={`${label}: ${strings.stepsProperties.rowCount}`}
              inputMode="numeric"
              placeholder={strings.stepsCountPlaceholder}
              value={draft.expectedCount}
              onChange={(event) => onChange({ expectedCount: event.target.value })}
            />
          </>
        ) : (
          <>
            <span className="hint">{strings.stepsOperators.equals}</span>
            <select
              {...common}
              aria-label={`${label}: ${strings.stepsCheckExpected}`}
              value={String(draft.expectedFlag)}
              onChange={(event) => onChange({ expectedFlag: event.target.value === 'true' })}
            >
              <option value="true">{strings.stepsYes}</option>
              <option value="false">{strings.stepsNo}</option>
            </select>
          </>
        )}
      </div>
    </>
  )
}
