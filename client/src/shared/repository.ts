// What the object repository accepts and how the Spy suggests a new object's properties
// (#25, FR-06). Pure functions, shared by the renderer and the tests.

import type { ElementDescriptor } from './element.ts'
import type { SnapshotNode } from './snapshot.ts'

/**
 * Descriptor fields that can identify an element: everything except what ADR
 * 2026-10-31-element-descriptor-v0 §3 never matches on (bounds, dpi, nativeWindowHandle,
 * frameworkId, enabled, offscreen) and nearestLabelSource. The server refuses the rest.
 * The ADR's priority comes first, then controlType, then fields that rarely identify alone.
 */
export const IDENTIFYING_FIELDS = [
  'automationId',
  'name',
  'nearestLabel',
  'className',
  'parentPath',
  'controlType',
  'windowTitle',
  'siblingIndex',
  'helpText',
  'accessKey',
] as const satisfies readonly (keyof ElementDescriptor)[]

export type IdentifyingField = (typeof IDENTIFYING_FIELDS)[number]

/** Property → value, best first; the server stores the order. */
export type PropertySet = Partial<Pick<ElementDescriptor, IdentifyingField>>

/** Where a property goes in the new object. */
export type PropertyUse = 'primary' | 'fallback' | 'unused'

/** `$defs.logicalName` of `schemas/step.schema.json`: `screen.element`. */
export const LOGICAL_NAME = /^[a-z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*$/

/** The AI service's "no object fits" (`ai/API.md`, #71); never a real object. */
export const NO_MATCH = 'none.noMatch'

export type NameProblem = 'blank' | 'form' | 'reserved'

/** Why `name` (trimmed) cannot be a logical name, or null when it can. */
export function logicalNameProblem(name: string): NameProblem | null {
  const text = name.trim()
  if (!text) return 'blank'
  if (!LOGICAL_NAME.test(text)) return 'form'
  if (text === NO_MATCH) return 'reserved'
  return null
}

const GENERATED_ID = /^(?:\d+|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$/
const QT_FALLBACK_LEAF = /^Q[A-Z]\w*?\d*$/

/**
 * True when an AutomationId looks machine-made: whole-string digits, a GUID, or a dotted Qt
 * id whose leaf is a class name (`…QPushButton2`). Same rule as the agent's
 * `model.is_generated_id` (ADR descriptor v0 §3).
 */
export function isGeneratedId(id: string): boolean {
  const text = id.trim()
  if (!text) return false
  const leaf = text.slice(text.lastIndexOf('.') + 1)
  return GENERATED_ID.test(text) || GENERATED_ID.test(leaf) || QT_FALLBACK_LEAF.test(leaf)
}

/** How many elements of the snapshot have every property of `set`. */
export function matchCount(set: PropertySet, elements: readonly SnapshotNode[]): number {
  const entries = Object.entries(set)
  return elements.filter(({ element }) =>
    entries.every(([field, value]) => element[field as IdentifyingField] === value),
  ).length
}

/**
 * Suggests where each of the element's identifying properties goes. Primary takes the
 * priority's fields in order, keeping only those that narrow the matches in this window,
 * until the element is the only match; the remaining priority fields become fallback. A
 * generated AutomationId and the rarely-identifying fields stay unused. The user edits all
 * of it before saving.
 */
export function suggestUses(
  element: ElementDescriptor,
  elements: readonly SnapshotNode[],
): Partial<Record<IdentifyingField, PropertyUse>> {
  const priority = IDENTIFYING_FIELDS.slice(0, IDENTIFYING_FIELDS.indexOf('controlType') + 1)
  const uses: Partial<Record<IdentifyingField, PropertyUse>> = {}
  const primary: PropertySet = {}
  let matches = elements.length
  for (const field of IDENTIFYING_FIELDS) {
    const value = element[field]
    if (value === undefined) continue
    const usable =
      priority.includes(field) && !(field === 'automationId' && isGeneratedId(String(value)))
    if (!usable) {
      uses[field] = 'unused'
      continue
    }
    const first = Object.keys(primary).length === 0
    const narrowed = matchCount({ ...primary, [field]: value }, elements)
    if (first || (matches > 1 && narrowed < matches)) {
      Object.assign(primary, { [field]: value })
      uses[field] = 'primary'
      matches = narrowed
    } else {
      uses[field] = 'fallback'
    }
  }
  return uses
}
