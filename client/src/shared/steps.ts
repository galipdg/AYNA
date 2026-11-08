// Test steps (`schemas/step.schema.json`, ADR 2026-10-27-step-schema-v0) and the codeless
// editor's row model (#38). Kept free of Electron and DOM imports so plain `node --test` can
// use it.

import stepSchema from '../../../schemas/step.schema.json' with { type: 'json' }
import { LOGICAL_NAME } from './repository.ts'

/**
 * The `version` const of the schema file the client is built with, which is also the file the
 * server reads, so a schema release cannot leave the editor saving an old version.
 */
export const STEP_SCHEMA_VERSION: string = stepSchema.properties.version.const

export const KEYWORDS = ['Click', 'Type', 'Select', 'Verify', 'Wait'] as const
export type Keyword = (typeof KEYWORDS)[number]

export const CHECK_PROPERTIES = [
  'name',
  'value',
  'enabled',
  'visible',
  'checked',
  'selected',
] as const
export type CheckProperty = (typeof CHECK_PROPERTIES)[number]

export const OPERATORS = ['equals', 'notEquals', 'contains'] as const
export type Operator = (typeof OPERATORS)[number]

export interface Checkpoint {
  property: CheckProperty
  operator: Operator
  /** A string for `name` and `value`, a boolean for the other properties. */
  expected: string | boolean
}

export interface Step {
  /** Assigned by the server on save. */
  id?: string
  keyword: Keyword
  /** Logical name of a repository object. */
  target: string
  /** Type and Select only. */
  value?: string
  /** Verify only. */
  checkpoint?: Checkpoint
  timeoutMs?: number
}

export interface StepDocument {
  version: typeof STEP_SCHEMA_VERSION
  steps: Step[]
}

/** `name` and `value` compare text; the others are true or false and allow only `equals`. */
export function isTextProperty(property: CheckProperty): boolean {
  return property === 'name' || property === 'value'
}

/** Keywords that take a value (the text to type, the item to choose). */
export function takesValue(keyword: Keyword | ''): boolean {
  return keyword === 'Type' || keyword === 'Select'
}

/**
 * One row of the step table as the user edits it. Every field is kept while the action
 * changes, so switching Type → Click → Type does not lose the text; `toStep` sends only the
 * fields the action uses.
 */
export interface DraftStep {
  /** Local key for the row; not saved. */
  key: string
  id?: string
  keyword: Keyword | ''
  target: string
  value: string
  property: CheckProperty
  operator: Operator
  /** The expected text for `name` and `value`. */
  expectedText: string
  /** The expected state for the other properties. */
  expectedFlag: boolean
  /** "Wait up to", in seconds as typed; empty means the run's default. */
  timeout: string
}

let nextKey = 0

/** A fresh row: Click, no element yet. */
export function newDraft(): DraftStep {
  return {
    key: `draft-${++nextKey}`,
    keyword: 'Click',
    target: '',
    value: '',
    property: 'name',
    operator: 'equals',
    expectedText: '',
    expectedFlag: true,
    timeout: '',
  }
}

/**
 * Rows with the ids a save gave them, found by row key. A row whose step no longer exists on
 * the server loses its id, so bringing it back with undo creates a new step.
 */
export function withStoredIds(drafts: DraftStep[], ids: Map<string, string | undefined>) {
  return drafts.map((draft) => ({ ...draft, id: ids.get(draft.key) }))
}

/**
 * The rows for a stored document's steps; `locale` (the UI language's, e.g. `tr-TR`) writes
 * "wait up to" with its decimal separator.
 */
export function draftsFrom(document: StepDocument, locale: string): DraftStep[] {
  return document.steps.map((step) => {
    const draft = newDraft()
    const { checkpoint } = step
    return {
      ...draft,
      ...(step.id ? { id: step.id } : {}),
      keyword: step.keyword,
      target: step.target,
      value: step.value ?? '',
      ...(checkpoint
        ? {
            property: checkpoint.property,
            operator: checkpoint.operator,
            expectedText: typeof checkpoint.expected === 'string' ? checkpoint.expected : '',
            expectedFlag: typeof checkpoint.expected === 'boolean' ? checkpoint.expected : true,
          }
        : {}),
      timeout: step.timeoutMs === undefined ? '' : secondsText(step.timeoutMs, locale),
    }
  })
}

/**
 * The rows with every "wait up to" that is a number written in `locale`, after a language
 * change; a text that is not a number stays as typed so its problem stays visible.
 */
export function withTimeoutsIn(drafts: DraftStep[], locale: string): DraftStep[] {
  return drafts.map((draft) => {
    const ms = parseSeconds(draft.timeout)
    if (typeof ms !== 'number') return draft
    const timeout = secondsText(ms, locale)
    return timeout === draft.timeout ? draft : { ...draft, timeout }
  })
}

/**
 * Old logical name → new one for every object whose name changed between two loads of the
 * element list (renamed in the Repository), matched by object id.
 */
export function renamedTargets(
  before: { id: string; name: string }[],
  after: { id: string; name: string }[],
): Map<string, string> {
  const old = new Map(before.map((object) => [object.id, object.name]))
  const renames = new Map<string, string>()
  for (const { id, name } of after) {
    const previous = old.get(id)
    if (previous !== undefined && previous !== name) renames.set(previous, name)
  }
  return renames
}

/**
 * The rows with their elements' new names. The server renames the stored steps itself
 * (FR-08), so an open test that kept the old names would mark them unknown and write them
 * back on save.
 */
export function withRenamedTargets(drafts: DraftStep[], renames: Map<string, string>): DraftStep[] {
  return drafts.map((draft) => {
    const target = renames.get(draft.target)
    return target === undefined ? draft : { ...draft, target }
  })
}

/**
 * The step document for the rows. A row that is not complete yet still becomes a step, with
 * what it has, so the schema check can say what is missing.
 */
export function documentFrom(drafts: DraftStep[]): StepDocument {
  return { version: STEP_SCHEMA_VERSION, steps: drafts.map(toStep) }
}

function toStep(draft: DraftStep): Step {
  const step: Record<string, unknown> = {}
  if (draft.id) step.id = draft.id
  if (draft.keyword) step.keyword = draft.keyword
  if (draft.target) step.target = draft.target
  if (takesValue(draft.keyword)) step.value = draft.value
  if (draft.keyword === 'Verify') {
    const text = isTextProperty(draft.property)
    step.checkpoint = {
      property: draft.property,
      operator: text ? draft.operator : 'equals',
      expected: text ? draft.expectedText : draft.expectedFlag,
    }
  }
  const timeoutMs = parseSeconds(draft.timeout)
  if (typeof timeoutMs === 'number') step.timeoutMs = timeoutMs
  return step as unknown as Step
}

/**
 * "Wait up to" as typed → milliseconds: undefined for empty, null when it is not a number of
 * seconds (a decimal comma is fine, at most millisecond precision).
 */
export function parseSeconds(text: string): number | undefined | null {
  const trimmed = text.trim()
  if (!trimmed) return undefined
  if (!/^\d+(?:[.,]\d{1,3})?$/.test(trimmed)) return null
  return Math.round(Number(trimmed.replace(',', '.')) * 1000)
}

/**
 * Milliseconds as seconds in the UI language: `2,5` in Turkish, `2.5` in English (ADR
 * client-ui-language: numbers follow the language). No digit grouping, since `parseSeconds`
 * would read Turkish `1.000` as one second.
 */
export function secondsText(ms: number, locale: string): string {
  return (ms / 1000).toLocaleString(locale, { maximumFractionDigits: 3, useGrouping: false })
}

/** Why a step cannot be saved; each code has one sentence in the UI. */
export type StepProblemCode =
  | 'keyword-missing' // no action, or one the schema does not know
  | 'target-missing'
  | 'target-unknown' // no saved element by that name in this application
  | 'target-invalid' // not a logical name
  | 'value-missing'
  | 'value-empty' // Select needs the item's text
  | 'value-too-long'
  | 'value-not-allowed'
  | 'checkpoint-invalid'
  | 'timeout-number'
  | 'timeout-range'
  | 'invalid' // anything else the schema refuses; the server's message when it sent one

/** The cell a problem belongs to, so the table can mark it. */
export type StepField = 'keyword' | 'target' | 'value' | 'timeout' | 'step'

export const PROBLEM_FIELD: Record<StepProblemCode, StepField> = {
  'keyword-missing': 'keyword',
  'target-missing': 'target',
  'target-unknown': 'target',
  'target-invalid': 'target',
  'value-missing': 'value',
  'value-empty': 'value',
  'value-too-long': 'value',
  'value-not-allowed': 'value',
  'checkpoint-invalid': 'value',
  'timeout-number': 'timeout',
  'timeout-range': 'timeout',
  invalid: 'step',
}

export interface StepProblem {
  /** The step's position, from 0; -1 for the document itself. */
  index: number
  code: StepProblemCode
  /** The server's own words, for `invalid` from a save. */
  message?: string
}

/** The parts of an Ajv error that `schemaProblems` reads. */
export interface SchemaError {
  instancePath: string
  keyword: string
  params: Record<string, unknown>
}

const REQUIRED: Record<string, StepProblemCode> = {
  keyword: 'keyword-missing',
  target: 'target-missing',
  value: 'value-missing',
  checkpoint: 'checkpoint-invalid',
}

/** Turns Ajv's errors for a step document into one problem per step and reason. */
export function schemaProblems(errors: SchemaError[]): StepProblem[] {
  return unique(
    errors.flatMap((error): StepProblem[] => {
      const match = /^\/steps\/(\d+)(\/[^/]+)?/.exec(error.instancePath)
      if (!match) return [{ index: -1, code: 'invalid' }]
      const index = Number(match[1])
      const field = match[2]?.slice(1)
      // `if` and `allOf` repeat what the error inside them already says.
      if (error.keyword === 'if' || error.keyword === 'allOf') return []
      if (field === undefined) {
        const missing = REQUIRED[String(error.params.missingProperty)]
        return [{ index, code: error.keyword === 'required' && missing ? missing : 'invalid' }]
      }
      return [{ index, code: fieldProblem(field, error) }]
    }),
  )
}

function fieldProblem(field: string, error: SchemaError): StepProblemCode {
  const { keyword, instancePath } = error
  switch (field) {
    case 'keyword':
      return 'keyword-missing'
    case 'target':
      return 'target-invalid'
    case 'value':
      if (keyword === 'false schema') return 'value-not-allowed'
      if (keyword === 'minLength') return 'value-empty'
      if (keyword === 'maxLength') return 'value-too-long'
      return 'invalid'
    case 'checkpoint':
      return instancePath.endsWith('/expected') && keyword === 'maxLength'
        ? 'value-too-long'
        : 'checkpoint-invalid'
    case 'timeoutMs':
      return 'timeout-range'
    default:
      return 'invalid'
  }
}

/**
 * What the schema cannot see: a "Wait up to" that is not a number, and an element that is not
 * in the repository. `targets` is null while the repository list is not loaded.
 */
export function localProblems(drafts: DraftStep[], targets: Set<string> | null): StepProblem[] {
  return drafts.flatMap((draft, index): StepProblem[] => {
    const problems: StepProblem[] = []
    if (parseSeconds(draft.timeout) === null) problems.push({ index, code: 'timeout-number' })
    if (targets && LOGICAL_NAME.test(draft.target) && !targets.has(draft.target)) {
      problems.push({ index, code: 'target-unknown' })
    }
    return problems
  })
}

/**
 * The server's refused fields (`$.steps[3].target`) as step problems; an unknown element gets
 * the editor's own text, anything else keeps the server's message.
 */
export function serverProblems(fields: { path: string; message: string }[]): StepProblem[] {
  return unique(
    fields.map(({ path, message }): StepProblem => {
      const match = /^\$\.steps\[(\d+)\](?:\.(\w+))?/.exec(path)
      const index = match ? Number(match[1]) : -1
      if (match?.[2] === 'target' && message.startsWith('No repository object named')) {
        return { index, code: 'target-unknown' }
      }
      return { index, code: 'invalid', message }
    }),
  )
}

const COLUMNS: StepField[] = ['keyword', 'target', 'value', 'timeout', 'step']

/** Problems in step order, then in column order; each step and reason once. */
export function unique(problems: StepProblem[]): StepProblem[] {
  const seen = new Set<string>()
  const column = (problem: StepProblem) => COLUMNS.indexOf(PROBLEM_FIELD[problem.code])
  return problems
    .filter((problem) => {
      const id = `${problem.index} ${problem.code} ${problem.message ?? ''}`
      if (seen.has(id)) return false
      seen.add(id)
      return true
    })
    .sort((a, b) => a.index - b.index || column(a) - column(b))
}

/** Moves the item at `from` to `to` (both positions in the original list). */
export function move<T>(items: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || from >= items.length || to < 0 || to >= items.length) {
    return items
  }
  const next = [...items]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}
